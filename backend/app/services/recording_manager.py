import asyncio
import base64
import time
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class RecordingSession:
    """Manages a single recording session with Playwright browser instance."""

    VIEWPORT_WIDTH = 1280
    VIEWPORT_HEIGHT = 720
    TARGET_FPS = 10
    JPEG_QUALITY = 60

    def __init__(self, session_id: str, url: str, browser):
        self.session_id = session_id
        self.url = url
        self.browser = browser
        self.context = None
        self.page = None
        self.cdp_session = None
        self.is_recording = False
        self.actions: list[dict] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._push_task: asyncio.Task | None = None

    async def start(self):
        self.context = await self.browser.new_context(
            viewport={"width": self.VIEWPORT_WIDTH, "height": self.VIEWPORT_HEIGHT}
        )
        self.page = await self.context.new_page()
        await self.page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
        self.cdp_session = await self.page.context.new_cdp_session(self.page)
        self.is_recording = True
        self.actions.append({"type": "goto", "url": self.url})

    async def capture_frame(self) -> bytes:
        result = await self.cdp_session.send(
            "Page.captureScreenshot",
            {
                "format": "jpeg",
                "quality": self.JPEG_QUALITY,
                "clip": {
                    "x": 0,
                    "y": 0,
                    "width": self.VIEWPORT_WIDTH,
                    "height": self.VIEWPORT_HEIGHT,
                    "scale": 1,
                },
            },
        )
        return base64.b64decode(result["data"])

    async def push_frames(self, ws: WebSocket):
        interval = 1.0 / self.TARGET_FPS
        while self.is_recording:
            t0 = time.monotonic()
            try:
                frame_data = await self.capture_frame()
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_bytes(frame_data)
            except Exception:
                pass
            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0, interval - elapsed))

    def start_push(self, ws: WebSocket):
        self._push_task = asyncio.create_task(self.push_frames(ws))

    def stop_push(self):
        if self._push_task and not self._push_task.done():
            self._push_task.cancel()
            self._push_task = None

    async def get_selector_at(self, x: int, y: int) -> str:
        try:
            return await self.page.evaluate(
                """(coords) => {
                    const el = document.elementFromPoint(coords.x, coords.y);
                    if (!el) return '';
                    if (el.id) return '#' + CSS.escape(el.id);
                    const path = [];
                    let cur = el;
                    while (cur && cur.nodeType === Node.ELEMENT_NODE) {
                        let sel = cur.tagName.toLowerCase();
                        if (cur.id) { path.unshift('#' + CSS.escape(cur.id)); break; }
                        const parent = cur.parentElement;
                        if (parent) {
                            const siblings = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
                            if (siblings.length > 1) {
                                sel += ':nth-of-type(' + (siblings.indexOf(cur) + 1) + ')';
                            }
                        }
                        path.unshift(sel);
                        cur = cur.parentElement;
                    }
                    return path.join(' > ');
                }""",
                {"x": x, "y": y},
            )
        except Exception:
            return ""

    async def handle_event(self, event: dict):
        event_type = event.get("type")
        try:
            if event_type == "click":
                x, y = event["x"], event["y"]
                selector = await self.get_selector_at(x, y)
                await self.page.mouse.click(x, y)
                self.actions.append(
                    {"type": "click", "x": x, "y": y, "selector": selector}
                )
            elif event_type == "dblclick":
                x, y = event["x"], event["y"]
                selector = await self.get_selector_at(x, y)
                await self.page.mouse.dblclick(x, y)
                self.actions.append(
                    {"type": "dblclick", "x": x, "y": y, "selector": selector}
                )
            elif event_type == "mousedown":
                x, y = event["x"], event["y"]
                await self.page.mouse.move(x, y)
                await self.page.mouse.down()
                self.actions.append({"type": "mousedown", "x": x, "y": y})
            elif event_type == "mousemove":
                x, y = event["x"], event["y"]
                await self.page.mouse.move(x, y)
                self.actions.append({"type": "mousemove", "x": x, "y": y})
            elif event_type == "mouseup":
                x, y = event["x"], event["y"]
                await self.page.mouse.move(x, y)
                await self.page.mouse.up()
                self.actions.append({"type": "mouseup", "x": x, "y": y})
            elif event_type == "type":
                text = event["text"]
                await self.page.keyboard.type(text)
                self.actions.append({"type": "type", "text": text})
            elif event_type == "keypress":
                key = event["key"]
                await self.page.keyboard.press(key)
                self.actions.append({"type": "keypress", "key": key})
            elif event_type == "scroll":
                dx, dy = event.get("deltaX", 0), event.get("deltaY", 0)
                await self.page.mouse.wheel(dx, dy)
                self.actions.append({"type": "scroll", "deltaX": dx, "deltaY": dy})
            elif event_type == "navigate":
                url = event["url"]
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                self.actions.append({"type": "goto", "url": url})
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[RecordingSession] handle_event error: {e}")

    def generate_script(self) -> str:
        lines = [
            "from playwright.sync_api import sync_playwright",
            "",
            "",
            "def run(playwright):",
            "    browser = playwright.chromium.launch(headless=True)",
            "    page = browser.new_page()",
        ]
        for action in self.actions:
            atype = action["type"]
            if atype == "goto":
                lines.append(f'    page.goto("{action["url"]}")')
            elif atype == "click":
                sel = action.get("selector", "")
                if sel:
                    lines.append(f'    page.click("{sel}")')
                else:
                    lines.append(
                        f'    page.mouse.click({action["x"]}, {action["y"]})'
                    )
            elif atype == "dblclick":
                sel = action.get("selector", "")
                if sel:
                    lines.append(f'    page.dblclick("{sel}")')
                else:
                    lines.append(
                        f'    page.mouse.dblclick({action["x"]}, {action["y"]})'
                    )
            elif atype == "mousedown":
                lines.append(f'    page.mouse.move({action["x"]}, {action["y"]})')
                lines.append('    page.mouse.down()')
            elif atype == "mousemove":
                lines.append(f'    page.mouse.move({action["x"]}, {action["y"]})')
            elif atype == "mouseup":
                lines.append(f'    page.mouse.move({action["x"]}, {action["y"]})')
                lines.append('    page.mouse.up()')
            elif atype == "type":
                text = action["text"].replace('"', '\\"')
                lines.append(f'    page.keyboard.type("{text}")')
            elif atype == "keypress":
                lines.append(f'    page.keyboard.press("{action["key"]}")')
            elif atype == "scroll":
                lines.append(
                    f'    page.mouse.wheel({action["deltaX"]}, {action["deltaY"]})'
                )
        lines.extend([
            "    browser.close()",
            "",
            "",
            "with sync_playwright() as p:",
            "    run(p)",
            "",
        ])
        return "\n".join(lines)

    async def cleanup(self):
        self.is_recording = False
        self.stop_push()
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass


class RecordingManager:
    """Singleton managing all recording sessions."""

    def __init__(self):
        self._sessions: dict[str, RecordingSession] = {}
        self._playwright = None
        self._browser = None

    async def get_playwright(self):
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
        return self._playwright

    async def _ensure_browser(self):
        if self._browser is None or not self._browser.is_connected():
            pw = await self.get_playwright()
            self._browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
        return self._browser

    async def create_session(self, session_id: str, url: str) -> RecordingSession:
        browser = await self._ensure_browser()
        session = RecordingSession(session_id, url, browser)
        await session.start()
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> RecordingSession | None:
        return self._sessions.get(session_id)

    async def remove_session(self, session_id: str) -> dict | None:
        session = self._sessions.pop(session_id, None)
        if session:
            script = session.generate_script()
            url = session.url
            await session.cleanup()
            return {"script": script, "url": url}
        return None

    async def shutdown(self):
        for sid in list(self._sessions):
            session = self._sessions.pop(sid)
            await session.cleanup()
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


recording_manager = RecordingManager()
