"""Task executors for different test types."""

import asyncio
import base64
import json
import logging
import tempfile
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """Base class for task executors."""

    @abstractmethod
    async def execute(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test case and return the result."""
        pass


class PlaywrightExecutor(BaseExecutor):
    """Executor for Playwright UI tests."""

    async def execute(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a UI test case using Playwright."""
        script = case_data.get("ui_script")
        if not script:
            return {"status": "FAILED", "detail": {"error": "未配置UI脚本"}}

        # Get stored screenshots and line_to_action mapping
        stored_screenshots = []
        line_to_action = []
        ui_screenshots = case_data.get("ui_screenshots")
        if ui_screenshots:
            stored_screenshots = ui_screenshots.get("screenshots", [])
            line_to_action = ui_screenshots.get("line_to_action", [])

        # Parse script into steps
        script_lines = script.strip().split("\n")
        steps = []
        step_logs = []

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                for line_idx, line in enumerate(script_lines):
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("from ") or line.startswith("import ") or line.startswith("def ") or line.startswith("with ") or line == "browser.close()":
                        continue

                    if line.endswith(":"):
                        continue

                    step_info = {
                        "step_index": len(steps) + 1,
                        "code": line,
                        "status": "pending",
                        "log": "",
                        "screenshot": None,
                        "timestamp": None,
                    }

                    # Get corresponding screenshot from recording
                    action_idx = line_to_action[line_idx] if line_idx < len(line_to_action) else None
                    if action_idx is not None and action_idx < len(stored_screenshots):
                        step_info["screenshot"] = stored_screenshots[action_idx]

                    start_time = time.monotonic()
                    try:
                        if "page.goto(" in line:
                            url = line.split('"')[1] if '"' in line else line.split("'")[1]
                            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            step_info["log"] = f"导航到: {url}"
                        elif "page.click(" in line:
                            selector = line.split('"')[1] if '"' in line else line.split("'")[1]
                            await page.click(selector, timeout=10000)
                            step_info["log"] = f"点击元素: {selector}"
                        elif "page.dblclick(" in line:
                            selector = line.split('"')[1] if '"' in line else line.split("'")[1]
                            await page.dblclick(selector, timeout=10000)
                            step_info["log"] = f"双击元素: {selector}"
                        elif "page.keyboard.type(" in line:
                            text = line.split('"')[1] if '"' in line else line.split("'")[1]
                            await page.keyboard.type(text)
                            step_info["log"] = f"输入文本: {text}"
                        elif "page.keyboard.press(" in line:
                            key = line.split('"')[1] if '"' in line else line.split("'")[1]
                            await page.keyboard.press(key)
                            step_info["log"] = f"按键: {key}"
                        elif "page.mouse.click(" in line:
                            coords = line.split("(")[1].split(")")[0].split(",")
                            x, y = int(coords[0].strip()), int(coords[1].strip())
                            await page.mouse.click(x, y)
                            step_info["log"] = f"鼠标点击: ({x}, {y})"
                        elif "page.mouse.dblclick(" in line:
                            coords = line.split("(")[1].split(")")[0].split(",")
                            x, y = int(coords[0].strip()), int(coords[1].strip())
                            await page.mouse.dblclick(x, y)
                            step_info["log"] = f"鼠标双击: ({x}, {y})"
                        elif "page.mouse.move(" in line:
                            coords = line.split("(")[1].split(")")[0].split(",")
                            x, y = int(coords[0].strip()), int(coords[1].strip())
                            await page.mouse.move(x, y)
                            step_info["log"] = f"鼠标移动: ({x}, {y})"
                        elif "page.mouse.down()" in line:
                            await page.mouse.down()
                            step_info["log"] = "鼠标按下"
                        elif "page.mouse.up()" in line:
                            await page.mouse.up()
                            step_info["log"] = "鼠标释放"
                        elif "page.mouse.wheel(" in line:
                            coords = line.split("(")[1].split(")")[0].split(",")
                            dx, dy = int(coords[0].strip()), int(coords[1].strip())
                            await page.mouse.wheel(dx, dy)
                            step_info["log"] = f"滚动: ({dx}, {dy})"
                        elif "expect(" in line:
                            step_info["log"] = f"断言: {line.strip()}"
                            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                            step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                        else:
                            step_info["log"] = f"执行: {line}"

                        # Capture screenshot after action
                        if step_info["screenshot"] is None and "expect(" not in line:
                            try:
                                screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                                step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                            except Exception:
                                pass

                        step_info["status"] = "success"
                        step_info["duration_ms"] = int((time.monotonic() - start_time) * 1000)
                        step_info["timestamp"] = datetime.now(timezone.utc).isoformat()

                    except Exception as e:
                        step_info["status"] = "failed"
                        step_info["log"] = f"执行失败: {str(e)}"
                        step_info["duration_ms"] = int((time.monotonic() - start_time) * 1000)
                        step_info["timestamp"] = datetime.now(timezone.utc).isoformat()
                        try:
                            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                            step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                        except Exception:
                            pass
                        steps.append(step_info)
                        step_logs.append(f"[Step {step_info['step_index']}] FAILED: {line} - {str(e)}")
                        raise

                    steps.append(step_info)
                    step_logs.append(f"[Step {step_info['step_index']}] {step_info['status'].upper()}: {step_info['log']}")

                await browser.close()

            return {
                "status": "SUCCESS",
                "detail": {
                    "exit_code": 0,
                    "stdout": "\n".join(step_logs),
                    "stderr": "",
                    "steps": steps,
                    "total_steps": len(steps),
                },
            }

        except Exception as e:
            return {
                "status": "FAILED",
                "detail": {
                    "exit_code": 1,
                    "stdout": "\n".join(step_logs),
                    "stderr": str(e),
                    "steps": steps,
                    "total_steps": len(steps),
                    "error": f"脚本执行失败: {str(e)}",
                },
            }


class LocustExecutor(BaseExecutor):
    """Executor for Locust performance tests."""

    @staticmethod
    def _parse_locust_stats(stdout: str) -> Dict[str, Any]:
        """Parse Locust stdout text into structured stats."""
        import re
        stats: Dict[str, Any] = {"endpoints": [], "total": None}
        lines = stdout.strip().split("\n")

        table_started = False
        separator_idx = -1

        for i, line in enumerate(lines):
            if line.startswith("Name") and "# reqs" in line:
                table_started = True
                continue
            if table_started and set(line.strip()) <= {"-", " ", "+"}:
                separator_idx = i
                continue

        if not table_started or separator_idx < 0:
            return stats

        for line in lines[separator_idx + 1:]:
            line = line.strip()
            if not line or line.startswith("Aggregating"):
                continue
            if set(line) <= {"-", " ", "+"}:
                break

            parts = line.rsplit(None, 8)
            if len(parts) < 7:
                continue

            name = parts[0]
            try:
                reqs = int(parts[1])
                fails = int(parts[2])
                avg = float(parts[3])
                min_val = float(parts[4])
                max_val = float(parts[5])
                median = float(parts[6])
                rps = float(parts[7]) if len(parts) > 7 else 0
            except (ValueError, IndexError):
                continue

            entry = {
                "name": name,
                "requests": reqs,
                "failures": fails,
                "avg_ms": round(avg, 2),
                "min_ms": round(min_val, 2),
                "max_ms": round(max_val, 2),
                "median_ms": round(median, 2),
                "rps": round(rps, 2),
                "failure_rate": round(fails / reqs * 100, 2) if reqs > 0 else 0,
            }

            if name.lower() in ("aggregated", "total"):
                stats["total"] = entry
            else:
                stats["endpoints"].append(entry)

        if not stats["total"] and stats["endpoints"]:
            total_reqs = sum(e["requests"] for e in stats["endpoints"])
            total_fails = sum(e["failures"] for e in stats["endpoints"])
            total_rps = sum(e["rps"] for e in stats["endpoints"])
            total_avg = sum(e["avg_ms"] * e["requests"] for e in stats["endpoints"]) / total_reqs if total_reqs > 0 else 0
            stats["total"] = {
                "name": "Aggregated",
                "requests": total_reqs,
                "failures": total_fails,
                "avg_ms": round(total_avg, 2),
                "min_ms": min((e["min_ms"] for e in stats["endpoints"]), default=0),
                "max_ms": max((e["max_ms"] for e in stats["endpoints"]), default=0),
                "median_ms": 0,
                "rps": round(total_rps, 2),
                "failure_rate": round(total_fails / total_reqs * 100, 2) if total_reqs > 0 else 0,
            }

        for line in lines:
            if "p50" in line.lower() or "p95" in line.lower() or "p99" in line.lower():
                p_match = re.findall(r'(p\d+)[\s:]+([\d.]+)', line, re.IGNORECASE)
                if p_match and stats["total"]:
                    for p_name, p_val in p_match:
                        stats["total"][f"{p_name.lower()}_ms"] = round(float(p_val), 2)

        return stats

    async def execute(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a performance test case using Locust."""
        script = case_data.get("perf_script")
        if not script:
            return {"status": "FAILED", "detail": {"error": "未配置性能脚本"}}

        vusers = case_data.get("perf_vusers", 10)
        spawn_rate = case_data.get("perf_spawn_rate", 1)
        duration = case_data.get("perf_duration", 60)
        perf_url = case_data.get("perf_url", "http://localhost")

        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(script)
            script_path = f.name

        try:
            cmd = [
                "locust", "-f", script_path,
                "--headless",
                "-u", str(vusers),
                "-r", str(spawn_rate),
                "--run-time", f"{duration}s",
                "--host", perf_url,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=duration + 120,
            )

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            parsed_stats = self._parse_locust_stats(stdout_text)

            # Include stderr in output for debugging (connection errors, etc.)
            combined_output = stdout_text
            if stderr_text.strip():
                combined_output += "\n--- STDERR ---\n" + stderr_text

            detail = {
                "exit_code": proc.returncode,
                "vusers": vusers,
                "spawn_rate": spawn_rate,
                "duration": duration,
                "perf_url": perf_url,
                "output": combined_output[-3000:],
                "stats": parsed_stats,
            }

            if proc.returncode == 0:
                return {"status": "SUCCESS", "detail": detail}
            elif proc.returncode == 1:
                # Locust exit code 1 = test completed but had request failures (normal behavior)
                if parsed_stats.get("total") and parsed_stats["total"].get("requests", 0) > 0:
                    detail["error"] = "测试完成，存在失败请求"
                else:
                    # Exit code 1 with 0 requests = connection/script error
                    detail["error"] = "Locust 执行失败，请检查目标 URL 是否可达、脚本是否正确"
                return {"status": "FAILED", "detail": detail}
            else:
                detail["error"] = f"Locust 执行异常，退出码: {proc.returncode}"
                return {"status": "FAILED", "detail": detail}

        except asyncio.TimeoutError:
            return {"status": "FAILED", "detail": {"error": f"性能测试超时({duration + 120}s)"}}
        except FileNotFoundError:
            return {"status": "FAILED", "detail": {"error": "未安装 locust"}}
        except Exception as e:
            return {"status": "FAILED", "detail": {"error": str(e)}}
        finally:
            Path(script_path).unlink(missing_ok=True)


class ApiExecutor(BaseExecutor):
    """Executor for API tests."""

    async def execute(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API test case using httpx."""
        import httpx

        url = case_data.get("api_url")
        if not url:
            return {"status": "FAILED", "detail": {"error": "未配置接口URL"}}

        method = (case_data.get("api_method") or "GET").upper()
        headers = case_data.get("api_headers") or {}
        timeout = (case_data.get("api_timeout") or 30000) / 1000

        body = None
        api_body = case_data.get("api_body")
        if api_body and method in ("POST", "PUT", "PATCH"):
            body_type = case_data.get("api_body_type") or "JSON"
            if body_type == "JSON":
                try:
                    body = json.loads(api_body)
                except Exception:
                    body = api_body
            else:
                body = api_body

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method, url, headers=headers,
                json=body if isinstance(body, (dict, list)) else None,
                content=body if isinstance(body, str) else None,
            )

        detail = {
            "status_code": response.status_code,
            "url": str(response.url),
            "method": method,
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }

        try:
            detail["response_body"] = response.text[:5000]
        except Exception:
            detail["response_body"] = "<binary>"

        # Check assertions
        assertions = case_data.get("api_assertions") or []
        all_passed = True
        assertion_results = []

        if not assertions:
            passed = 200 <= response.status_code < 300
            assertion_results.append({
                "type": "status_code",
                "expected": "2xx",
                "actual": response.status_code,
                "passed": passed,
            })
            if not passed:
                all_passed = False
        else:
            for assertion in assertions:
                a_type = assertion.get("type", "")
                if a_type == "status_code":
                    expected = assertion.get("value")
                    passed = response.status_code == expected
                    assertion_results.append({
                        "type": "status_code",
                        "expected": expected,
                        "actual": response.status_code,
                        "passed": passed,
                    })
                elif a_type == "contains":
                    expected = assertion.get("value", "")
                    passed = expected in response.text
                    assertion_results.append({
                        "type": "contains",
                        "expected": expected,
                        "passed": passed,
                    })
                elif a_type == "json_path":
                    try:
                        data = json.loads(response.text)
                        path = assertion.get("path", "").split(".")
                        val = data
                        for p in path:
                            if p:
                                val = val[p]
                        expected = assertion.get("value")
                        passed = str(val) == str(expected)
                        assertion_results.append({
                            "type": "json_path",
                            "path": assertion.get("path"),
                            "expected": expected,
                            "actual": val,
                            "passed": passed,
                        })
                    except Exception as e:
                        assertion_results.append({
                            "type": "json_path",
                            "error": str(e),
                            "passed": False,
                        })
                        all_passed = False
                else:
                    assertion_results.append({
                        "type": a_type,
                        "passed": True,
                        "note": "未知断言类型，默认通过",
                    })

                if assertion_results and not assertion_results[-1].get("passed"):
                    all_passed = False

        detail["assertions"] = assertion_results
        status = "SUCCESS" if all_passed else "FAILED"
        if not all_passed:
            detail["error"] = "断言失败"

        return {"status": status, "detail": detail}
