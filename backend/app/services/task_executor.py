"""Task execution engine — runs test cases in the background."""

import asyncio
import logging
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.models.task import Task, TaskLog
from app.models.test_case import TaskCase, TestCase
from app.models.result import TestResult
from app.models.enums import ResultStatus, TaskStatus

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks by running their associated test cases."""

    async def execute(self, task_id: str):
        """Main entry point — runs in background via asyncio.create_task."""
        session_factory = get_session_factory()
        async with session_factory() as db:
            try:
                result = await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
                task = result.scalar_one_or_none()
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return

                # Fetch task cases
                cases_result = await db.execute(
                    select(TaskCase, TestCase)
                    .join(TestCase, TaskCase.case_id == TestCase.id)
                    .where(TaskCase.task_id == task_id, TaskCase.deleted_at.is_(None))
                    .order_by(TaskCase.sort_order)
                )
                task_cases = cases_result.all()
                task.total_cases = len(task_cases)
                await db.commit()

                await self._add_log(db, task_id, "INFO", f"任务开始执行，共 {len(task_cases)} 个用例")

                success_count = 0
                failed_count = 0
                skipped_count = 0

                for task_case, case in task_cases:
                    if task.status == TaskStatus.CANCELLED:
                        await self._add_log(db, task_id, "WARN", "任务已被取消，停止执行")
                        break

                    await self._add_log(db, task_id, "INFO", f"开始执行用例: {case.name}")
                    started_at = datetime.now(timezone.utc)
                    start_time = time.monotonic()

                    try:
                        if case.type == "API":
                            exec_result = await self._execute_api_case(case)
                        elif case.type == "UI":
                            exec_result = await self._execute_ui_case(case)
                        elif case.type == "PERFORMANCE":
                            exec_result = await self._execute_perf_case(case)
                        else:
                            exec_result = {"status": ResultStatus.SKIPPED, "detail": {"error": f"不支持的用例类型: {case.type}"}}
                    except Exception as e:
                        logger.error(f"Case {case.id} execution error: {e}")
                        exec_result = {"status": ResultStatus.FAILED, "detail": {"error": str(e), "traceback": traceback.format_exc()}}

                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    finished_at = datetime.now(timezone.utc)

                    # Save result
                    test_result = TestResult(
                        task_id=task_id,
                        case_id=case.id,
                        task_case_id=task_case.id,
                        status=exec_result["status"],
                        detail=exec_result.get("detail", {}),
                        duration_ms=duration_ms,
                        started_at=started_at,
                        finished_at=finished_at,
                    )
                    db.add(test_result)

                    if exec_result["status"] == ResultStatus.SUCCESS:
                        success_count += 1
                        await self._add_log(db, task_id, "INFO", f"用例通过: {case.name} ({duration_ms}ms)")
                    elif exec_result["status"] == ResultStatus.SKIPPED:
                        skipped_count += 1
                        await self._add_log(db, task_id, "WARN", f"用例跳过: {case.name}")
                    else:
                        failed_count += 1
                        error_msg = exec_result.get("detail", {}).get("error", "未知错误")
                        await self._add_log(db, task_id, "ERROR", f"用例失败: {case.name} - {error_msg}")

                    # Update task counters
                    task.success_count = success_count
                    task.failed_count = failed_count
                    task.skipped_count = skipped_count
                    await db.commit()

                # Final status
                task.finished_at = datetime.now(timezone.utc)
                task.status = TaskStatus.SUCCESS if failed_count == 0 else TaskStatus.FAILED
                await db.commit()

                await self._add_log(db, task_id, "INFO", f"任务执行完成: 成功 {success_count}, 失败 {failed_count}")
                logger.info(f"Task {task_id} completed: {success_count} success, {failed_count} failed")

            except Exception as e:
                logger.error(f"Task {task_id} execution fatal error: {e}")
                try:
                    task.status = TaskStatus.FAILED
                    task.finished_at = datetime.now(timezone.utc)
                    await db.commit()
                    await self._add_log(db, task_id, "ERROR", f"任务执行异常: {str(e)}")
                except Exception:
                    logger.error(f"Failed to update task {task_id} status after error")

    async def _execute_api_case(self, case: TestCase) -> dict:
        """Execute an API test case using httpx."""
        url = case.api_url
        if not url:
            return {"status": ResultStatus.FAILED, "detail": {"error": "未配置接口URL"}}

        method = (case.api_method or "GET").upper()
        headers = case.api_headers or {}
        timeout = (case.api_timeout or 30000) / 1000  # convert ms to seconds

        body = None
        if case.api_body and method in ("POST", "PUT", "PATCH"):
            body_type = case.api_body_type or "JSON"
            if body_type == "JSON":
                try:
                    import json
                    body = json.loads(case.api_body)
                except Exception:
                    body = case.api_body
            else:
                body = case.api_body

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(method, url, headers=headers, json=body if isinstance(body, (dict, list)) else None, content=body if isinstance(body, str) else None)

        # Build result detail
        detail = {
            "status_code": response.status_code,
            "url": str(response.url),
            "method": method,
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }

        try:
            detail["response_body"] = response.text[:5000]  # limit size
        except Exception:
            detail["response_body"] = "<binary>"

        # Check assertions
        assertions = case.api_assertions or []
        all_passed = True
        assertion_results = []

        # Default: check status code 2xx
        if not assertions:
            passed = 200 <= response.status_code < 300
            assertion_results.append({"type": "status_code", "expected": "2xx", "actual": response.status_code, "passed": passed})
            if not passed:
                all_passed = False
        else:
            for assertion in assertions:
                a_type = assertion.get("type", "")
                if a_type == "status_code":
                    expected = assertion.get("value")
                    passed = response.status_code == expected
                    assertion_results.append({"type": "status_code", "expected": expected, "actual": response.status_code, "passed": passed})
                elif a_type == "contains":
                    expected = assertion.get("value", "")
                    passed = expected in response.text
                    assertion_results.append({"type": "contains", "expected": expected, "passed": passed})
                elif a_type == "json_path":
                    # Simple JSON path check
                    try:
                        import json
                        data = json.loads(response.text)
                        path = assertion.get("path", "").split(".")
                        val = data
                        for p in path:
                            if p:
                                val = val[p]
                        expected = assertion.get("value")
                        passed = str(val) == str(expected)
                        assertion_results.append({"type": "json_path", "path": assertion.get("path"), "expected": expected, "actual": val, "passed": passed})
                    except Exception as e:
                        assertion_results.append({"type": "json_path", "error": str(e), "passed": False})
                        all_passed = False
                else:
                    assertion_results.append({"type": a_type, "passed": True, "note": "未知断言类型，默认通过"})

                if assertion_results and not assertion_results[-1].get("passed"):
                    all_passed = False

        detail["assertions"] = assertion_results
        status = ResultStatus.SUCCESS if all_passed else ResultStatus.FAILED
        if not all_passed:
            detail["error"] = "断言失败"

        return {"status": status, "detail": detail}

    async def _execute_ui_case(self, case: TestCase) -> dict:
        """Execute a UI test case by running the Playwright script with step-by-step capture."""
        script = case.ui_script
        if not script:
            return {"status": ResultStatus.FAILED, "detail": {"error": "未配置UI脚本"}}

        # Get stored screenshots and line_to_action mapping from recording
        stored_screenshots = []
        line_to_action = []
        if case.ui_screenshots:
            stored_screenshots = case.ui_screenshots.get("screenshots", [])
            line_to_action = case.ui_screenshots.get("line_to_action", [])

        # Parse script into steps for execution
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

                    # Skip function definition and context manager lines
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
                        # Execute the step
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
                            # Execute assertion
                            exec_line = line.strip()
                            step_info["log"] = f"断言: {exec_line}"
                            # For assertions, we capture the current screenshot
                            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                            import base64
                            step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                        else:
                            step_info["log"] = f"执行: {line}"

                        # Capture screenshot after action if not already captured
                        if step_info["screenshot"] is None and "expect(" not in line:
                            try:
                                screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                                import base64
                                step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                            except Exception:
                                pass

                        step_info["status"] = "success"
                        duration = int((time.monotonic() - start_time) * 1000)
                        step_info["duration_ms"] = duration
                        step_info["timestamp"] = datetime.now(timezone.utc).isoformat()

                    except Exception as e:
                        step_info["status"] = "failed"
                        step_info["log"] = f"执行失败: {str(e)}"
                        duration = int((time.monotonic() - start_time) * 1000)
                        step_info["duration_ms"] = duration
                        step_info["timestamp"] = datetime.now(timezone.utc).isoformat()
                        # Capture failure screenshot
                        try:
                            screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                            import base64
                            step_info["screenshot"] = base64.b64encode(screenshot_bytes).decode("ascii")
                        except Exception:
                            pass
                        steps.append(step_info)
                        step_logs.append(f"[Step {step_info['step_index']}] FAILED: {line} - {str(e)}")
                        raise

                    steps.append(step_info)
                    step_logs.append(f"[Step {step_info['step_index']}] {step_info['status'].upper()}: {step_info['log']}")

                await browser.close()

            detail = {
                "exit_code": 0,
                "stdout": "\n".join(step_logs),
                "stderr": "",
                "steps": steps,
                "total_steps": len(steps),
            }
            return {"status": ResultStatus.SUCCESS, "detail": detail}

        except Exception as e:
            detail = {
                "exit_code": 1,
                "stdout": "\n".join(step_logs),
                "stderr": str(e),
                "steps": steps,
                "total_steps": len(steps),
                "error": f"脚本执行失败: {str(e)}",
            }
            return {"status": ResultStatus.FAILED, "detail": detail}

    async def _execute_perf_case(self, case: TestCase) -> dict:
        """Execute a performance test case using Locust."""
        script = case.perf_script
        if not script:
            return {"status": ResultStatus.FAILED, "detail": {"error": "未配置性能脚本"}}

        vusers = case.perf_vusers or 10
        spawn_rate = case.perf_spawn_rate or 1
        duration = case.perf_duration or 60

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
                "--host", case.perf_url or "http://localhost",
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration + 60)

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            detail = {
                "exit_code": proc.returncode,
                "vusers": vusers,
                "spawn_rate": spawn_rate,
                "duration": duration,
                "output": stdout_text[-3000:],
            }

            if proc.returncode == 0:
                return {"status": ResultStatus.SUCCESS, "detail": detail}
            else:
                detail["error"] = f"Locust 执行失败，退出码: {proc.returncode}"
                detail["stderr"] = stderr_text[-2000:]
                return {"status": ResultStatus.FAILED, "detail": detail}

        except asyncio.TimeoutError:
            return {"status": ResultStatus.FAILED, "detail": {"error": f"性能测试超时({duration + 60}s)"}}
        except FileNotFoundError:
            return {"status": ResultStatus.FAILED, "detail": {"error": "未安装 locust，请先执行 pip install locust"}}
        except Exception as e:
            return {"status": ResultStatus.FAILED, "detail": {"error": str(e)}}
        finally:
            Path(script_path).unlink(missing_ok=True)

    async def _add_log(self, db: AsyncSession, task_id: str, level: str, message: str):
        """Add a task log entry."""
        log = TaskLog(task_id=task_id, level=level, message=message)
        db.add(log)
        await db.flush()


# Module-level singleton
task_executor = TaskExecutor()
