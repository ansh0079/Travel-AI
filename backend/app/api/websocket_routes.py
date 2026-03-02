from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.logging_config import get_logger
from app.utils.websocket_manager import connection_manager

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/research/{job_id}")
async def research_websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket channel for auto-research progress updates."""
    client_id = f"research_{job_id}"
    await connection_manager.connect(websocket, client_id)
    await connection_manager.subscribe_to_job(websocket, job_id)
    await websocket.send_json({"type": "connected", "job_id": job_id})

    logger.info("Research WebSocket connected", job_id=job_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "job_id": job_id})
            else:
                await websocket.send_json({"type": "ack", "job_id": job_id, "message": "received"})
    except WebSocketDisconnect:
        logger.info("Research WebSocket disconnected", job_id=job_id)
    except Exception as e:
        logger.error("Research WebSocket error", job_id=job_id, error=str(e), exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal Server Error")
        except Exception:
            pass
    finally:
        await connection_manager.unsubscribe_from_job(websocket, job_id)
        connection_manager.disconnect(websocket, client_id)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Generic WebSocket endpoint kept for backward compatibility."""
    await connection_manager.connect(websocket, client_id)
    logger.info("WebSocket connection established", client_id=client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", client_id=client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e), exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal Server Error")
        except Exception:
            pass
    finally:
        connection_manager.disconnect(websocket, client_id)


async def emit_research_started(job_id: str, preferences: dict):
    await connection_manager.broadcast_to_job(
        job_id,
        {
            "type": "started",
            "job_id": job_id,
            "message": "Research started",
            "preferences_summary": {
                "origin": preferences.get("origin", ""),
                "destinations_count": len(preferences.get("destinations", [])),
                "budget_level": preferences.get("budget_level", "moderate"),
            },
        },
    )


async def emit_research_progress(job_id: str, step: str, percentage: int, message: str):
    await connection_manager.broadcast_to_job(
        job_id,
        {
            "type": "progress",
            "job_id": job_id,
            "step": step,
            "percentage": percentage,
            "message": message,
        },
    )


async def emit_research_completed(job_id: str, results_summary: dict):
    await connection_manager.broadcast_to_job(
        job_id,
        {
            "type": "completed",
            "job_id": job_id,
            "results_summary": results_summary,
            "message": "Research completed",
        },
    )


async def emit_research_error(job_id: str, error: str):
    await connection_manager.broadcast_to_job(
        job_id,
        {
            "type": "error",
            "job_id": job_id,
            "error": error,
        },
    )
