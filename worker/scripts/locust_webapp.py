"""Custom Locust Web UI with dynamic script loading.

Runs Locust as a subprocess on port 8090 (internal) and a Flask proxy on
port 8089 (external) that adds:
- POST /load-case?case_id=xxx  — load a script from the shared volume
- GET  /auto-load?case_id=xxx  — load script then redirect to /
- All other requests are proxied to Locust's built-in web UI
"""

import importlib.util
import json
import logging
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("locust_webapp")

# Directories & ports
SCRIPTS_DIR = Path(os.environ.get("SCRIPTS_DIR", "/scripts"))
LOCUST_PORT = 8090   # Locust web UI (internal, not exposed by Docker)
PROXY_PORT = 8089     # Our proxy (external, port-mapped by Docker)

# Global state
locust_proc = None
current_case_id = None

# Placeholder script content (used when no case is loaded)
PLACEHOLDER_CONTENT = '''# Locust Web UI placeholder script
from locust import HttpUser, task, between

class PlaceholderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/")
'''


def _load_user_classes(script_path: str) -> list:
    """Import a Locust script and return all HttpUser subclasses."""
    spec = importlib.util.spec_from_file_location("_locust_case", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from locust import User
    return [cls for cls in mod.__dict__.values()
            if isinstance(cls, type) and issubclass(cls, User) and cls != User]


def _read_case_meta(case_id: str) -> dict:
    """Read performance parameter metadata for a case."""
    meta_path = SCRIPTS_DIR / f"{case_id}.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _do_load_case(case_id: str) -> dict:
    """Validate and load a Locust script by case_id."""
    global current_case_id

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

    # Read perf parameters from metadata
    meta = _read_case_meta(case_id)

    # Restart Locust subprocess with the new script and parameters
    _restart_locust(str(script_path), meta)
    current_case_id = case_id

    logger.info(f"Loaded case {case_id} ({len(user_classes)} user class(es), host={meta.get('perf_url', 'N/A')})")
    return {"ok": True, "case_id": case_id, "user_classes": len(user_classes), "meta": meta}


def _ensure_placeholder():
    """Ensure the placeholder script exists in SCRIPTS_DIR."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = SCRIPTS_DIR / "empty_locustfile.py"
    if not placeholder.exists():
        placeholder.write_text(PLACEHOLDER_CONTENT, encoding="utf-8")
        logger.info(f"Created placeholder script: {placeholder}")


def _start_locust(script_path: str = None, meta: dict = None):
    """Start the Locust web UI subprocess."""
    global locust_proc

    _ensure_placeholder()

    if not script_path:
        script_path = str(SCRIPTS_DIR / "empty_locustfile.py")

    if not Path(script_path).exists():
        logger.error(f"Script not found: {script_path}")
        return

    cmd = [
        sys.executable, "-m", "locust",
        "-f", script_path,
        "--web-host", "127.0.0.1",
        "--web-port", str(LOCUST_PORT),
    ]

    # Add perf parameters from metadata (only if not already in command line args)
    if meta:
        if meta.get("perf_url") and "--host" not in " ".join(sys.argv):
            cmd.extend(["--host", meta["perf_url"]])
        if meta.get("perf_vusers") and "-u" not in sys.argv:
            cmd.extend(["-u", str(meta["perf_vusers"])])
        if meta.get("perf_spawn_rate") and "-r" not in sys.argv:
            cmd.extend(["-r", str(meta["perf_spawn_rate"])])

    # Forward --host and other args from the original command line
    for arg in sys.argv[1:]:
        if arg not in cmd:
            cmd.append(arg)

    logger.info(f"Starting Locust: {' '.join(cmd)}")
    try:
        locust_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Locust process started, PID={locust_proc.pid}")
    except Exception as e:
        logger.error(f"Failed to start Locust: {e}")
        locust_proc = None


def _restart_locust(script_path: str, meta: dict = None):
    """Stop the running Locust process and start a new one."""
    global locust_proc

    if locust_proc and locust_proc.poll() is None:
        logger.info("Stopping previous Locust process...")
        locust_proc.terminate()
        try:
            locust_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            locust_proc.kill()
            locust_proc.wait(timeout=3)

    _start_locust(script_path, meta)


# ---------------------------------------------------------------------------
# Flask app — custom routes
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/status")
def status_route():
    running = locust_proc is not None and locust_proc.poll() is None
    meta = _read_case_meta(current_case_id) if current_case_id else {}
    return jsonify({
        "locust_running": running,
        "current_case_id": current_case_id,
        "locust_pid": locust_proc.pid if running else None,
        "perf_url": meta.get("perf_url", ""),
        "case_name": meta.get("case_name", ""),
        "scripts_dir": str(SCRIPTS_DIR),
        "scripts": [f.name for f in SCRIPTS_DIR.glob("*.py")] if SCRIPTS_DIR.exists() else [],
    })


@app.route("/load-case", methods=["POST", "GET"])
def load_case_route():
    case_id = request.args.get("case_id", "").strip()
    if not case_id:
        return jsonify({"ok": False, "error": "Missing case_id parameter"}), 400
    result = _do_load_case(case_id)
    if result["ok"]:
        return jsonify(result)
    return jsonify(result), result.get("status", 500)


@app.route("/auto-load")
def auto_load_route():
    case_id = request.args.get("case_id", "").strip()
    if not case_id:
        return redirect("/")
    result = _do_load_case(case_id)
    if result["ok"]:
        return redirect("/")
    return jsonify(result), result.get("status", 500)


# ---------------------------------------------------------------------------
# Proxy — forward everything else to Locust on port 8090
# ---------------------------------------------------------------------------
def _proxy_to_locust(**kwargs):
    """Forward the current request to the Locust subprocess."""
    import requests as http_requests

    if locust_proc is None or locust_proc.poll() is not None:
        rc = locust_proc.returncode if locust_proc else None
        logger.error(f"Locust process not running (returncode={rc})")
        return jsonify({"error": "Locust is not running", "returncode": rc}), 503

    target = f"http://127.0.0.1:{LOCUST_PORT}{request.full_path.rstrip('?')}"
    try:
        resp = http_requests.request(
            method=request.method,
            url=target,
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
        )
        hop = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in hop}
        return Response(resp.content, status=resp.status_code, headers=headers)
    except http_requests.ConnectionError:
        return jsonify({"error": "Cannot connect to Locust web UI"}), 502
    except http_requests.Timeout:
        return jsonify({"error": "Locust web UI timeout"}), 504
    except Exception as e:
        return jsonify({"error": f"Proxy error: {e}"}), 500


# Register catch-all proxy (lower priority than specific routes)
app.add_url_rule("/<path:path>", endpoint="path_proxy",
                 view_func=_proxy_to_locust,
                 methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
app.add_url_rule("/", endpoint="root_proxy",
                 view_func=_proxy_to_locust,
                 methods=["GET", "POST"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _shutdown(sig, frame):
    logger.info("Shutting down...")
    if locust_proc and locust_proc.poll() is None:
        locust_proc.terminate()
        try:
            locust_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            locust_proc.kill()
    sys.exit(0)


def main():
    global locust_proc

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Determine initial script
    default_case_id = os.environ.get("DEFAULT_CASE_ID", "")
    default_script = os.environ.get("DEFAULT_SCRIPT", "")
    initial_script = str(SCRIPTS_DIR / "empty_locustfile.py")

    if default_case_id:
        script_path = SCRIPTS_DIR / f"{default_case_id}.py"
        if script_path.exists():
            initial_script = str(script_path)
            logger.info(f"Auto-loading case {default_case_id}")
    elif default_script and Path(default_script).exists():
        initial_script = default_script

    _start_locust(initial_script)

    logger.info(f"Locust Web UI proxy ready on port {PROXY_PORT}")
    logger.info(f"  Load a case: POST /load-case?case_id=xxx")
    logger.info(f"  Auto-load:   GET  /auto-load?case_id=xxx")
    logger.info(f"  With query:  GET  /?case_id=xxx")

    app.run(host="0.0.0.0", port=PROXY_PORT, threaded=True)


if __name__ == "__main__":
    main()
