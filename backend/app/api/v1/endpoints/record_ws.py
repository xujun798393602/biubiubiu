import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.recording_manager import recording_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/record/{session_id}")
async def record_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = recording_manager.get_session(session_id)
    if not session:
        logger.warning(f"[RecordWS] Session not found: {session_id}")
        await websocket.close(code=4004, reason="Session not found")
        return

    logger.info(f"[RecordWS] Client connected, session: {session_id}")
    session.start_push(websocket)
    try:
        while session.is_recording:
            data = await websocket.receive_json()
            logger.info(f"[RecordWS] Received event: {data.get('type')}")
            if data.get("type") == "stop":
                break
            await session.handle_event(data)
    except WebSocketDisconnect:
        logger.info(f"[RecordWS] Client disconnected, session: {session_id}")
    except Exception as e:
        logger.error(f"[RecordWS] Error: {e}")
    finally:
        session.is_recording = False
        session.stop_push()
