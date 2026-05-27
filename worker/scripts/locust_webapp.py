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

    @app.route("/historical-results")
    def historical_results_route():
        """Display historical test results for a case, fetched from the platform backend."""
        case_id = request.args.get("case_id", "").strip()
        task_id = request.args.get("task_id", "").strip()
        token = request.args.get("token", "").strip()
        if not case_id:
            return "Missing case_id parameter", 400

        import urllib.request
        import urllib.error

        backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")
        api_url = f"{backend_url}/api/v1/results/by-case/{case_id}"

        try:
            req = urllib.request.Request(api_url)
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                api_resp = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            if e.code == 401:
                return """<html><head><meta charset="utf-8"><title>认证失败</title>
                <style>body{font-family:sans-serif;margin:40px;background:#fafafa}
                .err{background:#fef0f0;padding:16px;border-radius:4px;border-left:3px solid #f56c6c;color:#f56c6c}</style></head>
                <body><h3>认证失败</h3><div class="err">Token 已过期或无效，请返回平台重新打开此页面。</div>
                <p><a href="/">← 返回 Locust</a></p></body></html>""", 401
            return f"<h3>Backend error {e.code}</h3><pre>{body[:500]}</pre>", 502
        except Exception as e:
            return f"<h3>Failed to fetch results: {e}</h3><p>Backend: {backend_url}</p>", 502

        data = api_resp.get("data", {})
        case_name = data.get("case_name", case_id)
        results = data.get("results", [])

        # Find the latest completed result with stats
        latest = None
        for r in results:
            if r.get("status") in ("SUCCESS", "FAILED") and r.get("detail", {}).get("stats"):
                latest = r
                break

        if not latest:
            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Historical Results - {case_name}</title>
            <style>body{{font-family:sans-serif;margin:40px;background:#fafafa}}h2{{color:#303133}}
            .info{{background:#fdf6ec;padding:12px;border-radius:4px;border-left:3px solid #e6a23c;color:#e6a23c}}</style></head>
            <body><h2>📊 {case_name}</h2><div class="info">该用例暂无已完成的测试结果，或结果中无统计数据。</div>
            <p><a href="/">← 返回 Locust</a></p></body></html>"""
            return html

        detail = latest["detail"]
        stats = detail.get("stats") or {}
        total = stats.get("total") or {}
        endpoints = stats.get("endpoints") or []

        # Build endpoints table rows
        ep_rows = ""
        for ep in endpoints:
            fail_cls = ' class="danger"' if ep.get("failures", 0) > 0 else ""
            ep_rows += f"""<tr>
                <td>GET</td><td>{ep.get('name','')}</td>
                <td>{ep.get('requests',0)}</td><td{fail_cls}>{ep.get('failures',0)}</td>
                <td>{ep.get('median_ms',0)}</td><td>{ep.get('avg_ms',0)}</td>
                <td>{ep.get('min_ms',0)}</td><td>{ep.get('max_ms',0)}</td>
                <td>{ep.get('rps',0)}</td><td>{ep.get('failure_rate',0)}%</td>
            </tr>"""

        # Total row
        total_fail_cls = ' class="danger"' if total.get("failures", 0) > 0 else ""
        total_row = f"""<tr class="total-row">
            <td colspan="2"><strong>Aggregated</strong></td>
            <td>{total.get('requests',0)}</td><td{total_fail_cls}>{total.get('failures',0)}</td>
            <td>{total.get('median_ms',0)}</td><td>{total.get('avg_ms',0)}</td>
            <td>{total.get('min_ms',0)}</td><td>{total.get('max_ms',0)}</td>
            <td>{total.get('rps',0)}</td><td>{total.get('failure_rate',0)}%</td>
        </tr>"""

        # Build bar chart data for response times
        max_avg = max((ep.get("avg_ms", 0) for ep in endpoints), default=1) or 1
        max_reqs = max((ep.get("requests", 0) for ep in endpoints), default=1) or 1

        resp_bars = ""
        for ep in endpoints:
            w = max(ep.get("avg_ms", 0) / max_avg * 100, 2)
            name = ep.get("name", "")
            if len(name) > 35:
                name = name[:35] + "..."
            resp_bars += f'<div class="bar-row"><div class="bar-label" title="{ep.get("name","")}">{name}</div><div class="bar-track"><div class="bar-fill blue" style="width:{w}%"></div><span class="bar-val">{ep.get("avg_ms",0)}</span></div></div>'

        req_bars = ""
        for ep in endpoints:
            w = max(ep.get("requests", 0) / max_reqs * 100, 2)
            name = ep.get("name", "")
            if len(name) > 35:
                name = name[:35] + "..."
            req_bars += f'<div class="bar-row"><div class="bar-label" title="{ep.get("name","")}">{name}</div><div class="bar-track"><div class="bar-fill green" style="width:{w}%"></div><span class="bar-val">{ep.get("requests",0)}</span></div></div>'

        status_cls = "success" if latest["status"] == "SUCCESS" else "danger"
        status_text = "通过" if latest["status"] == "SUCCESS" else "失败"
        error_html = ""
        if detail.get("error"):
            error_html = f'<div class="alert alert-warn">⚠️ {detail["error"]}</div>'

        task_link = ""
        if task_id:
            task_link = f'<a href="/" class="btn">← 返回 Locust</a>'

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Results - {case_name}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:24px;background:#fafafa;color:#303133}}
h2{{margin:0 0 8px}}.subtitle{{color:#909399;font-size:13px;margin-bottom:20px}}
.status-badge{{display:inline-block;padding:2px 10px;border-radius:4px;font-size:13px;font-weight:600}}
.status-badge.success{{background:#f0f9eb;color:#67c23a}}.status-badge.danger{{background:#fef0f0;color:#f56c6c}}
.cards{{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap}}
.card{{background:#fff;border:1px solid #ebeef5;border-radius:8px;padding:16px 24px;min-width:140px;text-align:center}}
.card .label{{font-size:12px;color:#909399}}.card .value{{font-size:22px;font-weight:700;margin-top:4px}}
.card .value.danger{{color:#f56c6c}}.card .value.primary{{color:#409eff}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06)}}
th{{background:#f5f7fa;padding:10px 12px;text-align:left;font-size:13px;color:#606266;border-bottom:1px solid #ebeef5}}
td{{padding:8px 12px;font-size:13px;border-bottom:1px solid #ebeef5}}
tr:hover{{background:#f5f7fa}}.total-row{{background:#ecf5ff !important;font-weight:600}}
.danger{{color:#f56c6c}}.section{{margin:24px 0 12px;font-size:15px;font-weight:600;color:#303133}}
.chart-box{{background:#fff;border:1px solid #ebeef5;border-radius:8px;padding:20px;margin-bottom:16px}}
.chart-title{{font-size:14px;font-weight:600;margin-bottom:14px}}
.bar-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.bar-label{{width:220px;font-size:12px;color:#606266;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}}
.bar-track{{flex:1;height:24px;background:#e4e7ed;border-radius:4px;position:relative;overflow:hidden;display:flex;align-items:center}}
.bar-fill{{height:100%;border-radius:4px}}.bar-fill.blue{{background:linear-gradient(90deg,#409eff,#66b1ff)}}
.bar-fill.green{{background:linear-gradient(90deg,#67c23a,#85ce61)}}
.bar-val{{position:absolute;right:8px;font-size:11px;color:#303133;font-weight:600}}
.alert{{padding:10px 14px;border-radius:4px;margin-bottom:12px;font-size:13px}}
.alert-warn{{background:#fdf6ec;border-left:3px solid #e6a23c;color:#b88230}}
.btn{{display:inline-block;padding:6px 16px;background:#409eff;color:#fff;border-radius:4px;text-decoration:none;font-size:13px;margin-top:16px}}
.btn:hover{{background:#66b1ff}}
</style></head><body>
<h2>📊 {case_name}</h2>
<div class="subtitle">用例ID: {case_id} | 最近执行: {latest.get('started_at','N/A')} | 耗时: {round(detail.get('duration_ms',0)/1000,1)}s
<span class="status-badge {status_cls}">{status_text}</span></div>

{error_html}

<div class="cards">
  <div class="card"><div class="label">总请求数</div><div class="value">{total.get('requests',0)}</div></div>
  <div class="card"><div class="label">失败数</div><div class="value{' danger' if total.get('failures',0)>0 else ''}">{total.get('failures',0)}</div></div>
  <div class="card"><div class="label">失败率</div><div class="value{' danger' if total.get('failure_rate',0)>0 else ''}">{total.get('failure_rate',0)}%</div></div>
  <div class="card"><div class="label">平均响应</div><div class="value">{total.get('avg_ms',0)} ms</div></div>
  <div class="card"><div class="label">RPS</div><div class="value primary">{total.get('rps',0)}</div></div>
</div>

<div class="section">STATISTICS</div>
<table>
<thead><tr><th>Type</th><th>Name</th><th># Requests</th><th># Failures</th><th>Median</th><th>Average</th><th>Min</th><th>Max</th><th>RPS</th><th>Failure Rate</th></tr></thead>
<tbody>{ep_rows}{total_row}</tbody>
</table>

<div class="section">CHARTS</div>
<div class="chart-box">
  <div class="chart-title">Average Response Time (ms)</div>
  {resp_bars}
</div>
<div class="chart-box">
  <div class="chart-title">Total Requests</div>
  {req_bars}
</div>

{task_link}
</body></html>"""
        return html

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
