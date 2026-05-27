"""Custom Locust Web UI with dynamic script loading.

Uses Locust's programmatic API (Environment + create_web_ui) to run the
web UI directly, with custom routes for loading scripts from the shared volume.
No subprocess — no deadlocks.
"""

import importlib.util
import json
import logging
import os
import signal
import sys
import threading
import uuid
from pathlib import Path

from flask import jsonify, redirect, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("locust_webapp")

SCRIPTS_DIR = Path(os.environ.get("SCRIPTS_DIR", "/scripts"))

# Global state
env = None
web_ui = None
current_case_id = None
load_lock = threading.Lock()

PLACEHOLDER_CONTENT = '''# Locust Web UI placeholder script
from locust import HttpUser, task, between

class PlaceholderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/")
'''


def _ensure_placeholder():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = SCRIPTS_DIR / "empty_locustfile.py"
    if not placeholder.exists():
        placeholder.write_text(PLACEHOLDER_CONTENT, encoding="utf-8")
        logger.info(f"Created placeholder: {placeholder}")


def _load_user_classes(script_path: str) -> list:
    spec = importlib.util.spec_from_file_location("_locust_case", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from locust import User
    return [cls for cls in mod.__dict__.values()
            if isinstance(cls, type) and issubclass(cls, User) and cls != User]


def _read_case_meta(case_id: str) -> dict:
    meta_path = SCRIPTS_DIR / f"{case_id}.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _do_load_case(case_id: str) -> dict:
    global current_case_id, env

    try:
        uuid.UUID(case_id)
    except ValueError:
        return {"ok": False, "error": "Invalid case_id format", "status": 400}

    script_path = SCRIPTS_DIR / f"{case_id}.py"
    if not script_path.exists():
        return {"ok": False, "error": f"Script not found: {case_id}", "status": 404}

    try:
        user_classes = _load_user_classes(str(script_path))
    except SyntaxError as e:
        return {"ok": False, "error": f"Script syntax error: {e}", "status": 400}
    except Exception as e:
        return {"ok": False, "error": f"Failed to load script: {e}", "status": 400}

    if not user_classes:
        return {"ok": False, "error": "No User classes found in script", "status": 400}

    meta = _read_case_meta(case_id)

    # Stop existing runner
    if env.runner:
        env.runner.quit()
        env.runner.greenlet.join(timeout=5)
        env.runner = None

    # Update environment with new user classes and host
    env.user_classes = user_classes
    if meta.get("perf_url"):
        env.host = meta["perf_url"]
        env.parsed_options.host = meta["perf_url"]
    if meta.get("perf_vusers"):
        env.parsed_options.num_users = meta["perf_vusers"]
    if meta.get("perf_spawn_rate"):
        env.parsed_options.spawn_rate = meta["perf_spawn_rate"]

    # Restart runner
    env.runner = env.create_local_runner()
    current_case_id = case_id

    logger.info(f"Loaded case {case_id} | host={meta.get('perf_url', 'N/A')} | users={len(user_classes)}")
    return {"ok": True, "case_id": case_id, "user_classes": len(user_classes), "meta": meta}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global env, web_ui

    _ensure_placeholder()

    from locust.env import Environment

    # Determine initial script
    default_case_id = os.environ.get("DEFAULT_CASE_ID", "")
    default_script = os.environ.get("DEFAULT_SCRIPT", "")
    initial_script = str(SCRIPTS_DIR / "empty_locustfile.py")

    if default_case_id:
        sp = SCRIPTS_DIR / f"{default_case_id}.py"
        if sp.exists():
            initial_script = str(sp)
            logger.info(f"Auto-loading case {default_case_id}")
    elif default_script and Path(default_script).exists():
        initial_script = default_script

    # Load initial user classes
    try:
        initial_users = _load_user_classes(initial_script)
    except Exception:
        initial_users = []

    # Create environment with parsed options
    env = Environment(user_classes=initial_users or [])
    # Use Locust's own parser to get all default options
    from locust.argument_parser import get_parser
    parser = get_parser(default_config_files=[])
    env.parsed_options = parser.parse_args(["--web-host", "0.0.0.0", "--web-port", "8089"])
    web_ui = env.create_web_ui()

    # Create runner
    runner = env.create_local_runner()

    # Register custom routes on Locust's Flask app
    app = web_ui.app

    @app.route("/status")
    def status_route():
        running = env.runner is not None
        meta = _read_case_meta(current_case_id) if current_case_id else {}
        return jsonify({
            "locust_running": running,
            "current_case_id": current_case_id,
            "perf_url": meta.get("perf_url", ""),
            "case_name": meta.get("case_name", ""),
            "host": env.host or "",
            "user_classes": [cls.__name__ for cls in env.user_classes],
            "scripts_dir": str(SCRIPTS_DIR),
            "scripts": [f.name for f in SCRIPTS_DIR.glob("*.py")] if SCRIPTS_DIR.exists() else [],
        })

    @app.route("/load-case", methods=["POST", "GET"])
    def load_case_route():
        case_id = request.args.get("case_id", "").strip()
        if not case_id:
            return jsonify({"ok": False, "error": "Missing case_id parameter"}), 400
        with load_lock:
            result = _do_load_case(case_id)
        if result["ok"]:
            return jsonify(result)
        return jsonify(result), result.get("status", 500)

    @app.route("/auto-load")
    def auto_load_route():
        case_id = request.args.get("case_id", "").strip()
        if not case_id:
            return redirect("/")
        with load_lock:
            result = _do_load_case(case_id)
        if result.get("ok"):
            return redirect("/")
        return jsonify(result), result.get("status", 500)

    # Shutdown handler
    def _shutdown(sig, frame):
        logger.info("Shutting down...")
        if env.runner:
            env.runner.quit()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Locust Web UI ready on port 8089")
    logger.info(f"  Load a case: POST /load-case?case_id=xxx")
    logger.info(f"  Auto-load:   GET  /auto-load?case_id=xxx")
    logger.info(f"  Status:      GET  /status")

    # Start web UI (blocks)
    web_ui.greenlet.join()


if __name__ == "__main__":
    main()
