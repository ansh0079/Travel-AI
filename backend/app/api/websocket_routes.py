"""
WebSocket Routes for Real-time Updates
Handles live progress updates for research jobs and other real-time features
"""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])

# Store active connections
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Map job_id -> set of WebSocket connections
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        # Map user_id -> set of WebSocket connections (for user-wide updates)
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Global connections (for broadcast)
        self.global_connections: Set[WebSocket] = set()
    
    async def connect_to_job(self, websocket: WebSocket, job_id: str):
        """Connect a WebSocket to receive updates for a specific job"""
        await websocket.accept()
        if job_id not in self.job_connections:
            self.job_connections[job_id] = set()
        self.job_connections[job_id].add(websocket)
    
    async def connect_to_user(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket to receive updates for a specific user"""
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
    
    async def connect_global(self, websocket: WebSocket):
        """Connect a WebSocket to receive global broadcasts"""
        await websocket.accept()
        self.global_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: str = None, user_id: str = None):
        """Disconnect a WebSocket"""
        if job_id and job_id in self.job_connections:
            self.job_connections[job_id].discard(websocket)
            if not self.job_connections[job_id]:
                del self.job_connections[job_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        self.global_connections.discard(websocket)
    
    async def send_to_job(self, job_id: str, message: dict):
        """Send message to all connections watching a specific job"""
        if job_id not in self.job_connections:
            return
        
        disconnected = set()
        for connection in self.job_connections[job_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.job_connections[job_id].discard(conn)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a specific user"""
        if user_id not in self.user_connections:
            return
        
        disconnected = set()
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        for conn in disconnected:
            self.user_connections[user_id].discard(conn)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all global connections"""
        disconnected = set()
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        for conn in disconnected:
            self.global_connections.discard(conn)


# Global connection manager instance
manager = ConnectionManager()


# WebSocket endpoint for job-specific updates
@router.websocket("/ws/research/{job_id}")
async def research_websocket(
    websocket: WebSocket,
    job_id: str,
    token: str = Query(None)  # Optional auth token
):
    """
    WebSocket endpoint for real-time research job updates.
    
    Connect to: ws://localhost:8000/api/v1/ws/research/{job_id}
    
    Receive messages like:
    {
        "type": "progress",
        "job_id": "abc-123",
        "step": "researching_weather",
        "percentage": 45,
        "message": "Checking weather for Bali..."
    }
    
    {
        "type": "completed",
        "job_id": "abc-123",
        "message": "Research completed!"
    }
    
    {
        "type": "error",
        "job_id": "abc-123",
        "error": "Something went wrong"
    }
    """
    await manager.connect_to_job(websocket, job_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "message": f"Connected to research job {job_id}"
        })
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for messages from client (optional)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping/pong for connection health
                if message.get("action") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                
                # Handle subscription changes
                elif message.get("action") == "subscribe":
                    new_job_id = message.get("job_id")
                    if new_job_id and new_job_id != job_id:
                        # Unsubscribe from current job
                        manager.disconnect(websocket, job_id=job_id)
                        # Subscribe to new job
                        await manager.connect_to_job(websocket, new_job_id)
                        job_id = new_job_id
                        await websocket.send_json({
                            "type": "subscribed",
                            "job_id": job_id
                        })
                
                else:
                    # Echo back unknown actions
                    await websocket.send_json({
                        "type": "ack",
                        "received": message
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id=job_id)
    except Exception as e:
        logger.error("WebSocket error for job", job_id=job_id, error=str(e))
        manager.disconnect(websocket, job_id=job_id)


# WebSocket endpoint for user-wide updates
@router.websocket("/ws/user/{user_id}")
async def user_websocket(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(None)
):
    """
    WebSocket endpoint for user-wide real-time updates.
    Receives notifications for all jobs and activities for this user.

    Connect to: ws://localhost:8000/api/v1/ws/user/{user_id}
    """
    await manager.connect_to_user(websocket, user_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": f"Connected to user channel {user_id}"
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("action") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)
    except Exception as e:
        logger.error("WebSocket error for user", user_id=user_id, error=str(e))
        manager.disconnect(websocket, user_id=user_id)


# Global broadcast WebSocket (for system-wide announcements)
@router.websocket("/ws/global")
async def global_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for global broadcasts.
    Receives system-wide announcements and updates.
    
    Connect to: ws://localhost:8000/api/v1/ws/global
    """
    await manager.connect_global(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to global channel"
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("Global WebSocket error", error=str(e))
        manager.disconnect(websocket)


# Helper functions for emitting events

async def emit_research_progress(
    job_id: str,
    step: str,
    percentage: int,
    message: str = "",
    extra_data: dict = None
):
    """Emit a progress update for a research job"""
    payload = {
        "type": "progress",
        "job_id": job_id,
        "step": step,
        "percentage": percentage,
        "message": message,
        "timestamp": asyncio.get_event_loop().time()
    }
    if extra_data:
        payload.update(extra_data)
    
    await manager.send_to_job(job_id, payload)


async def emit_research_completed(job_id: str, results_summary: dict = None):
    """Emit completion event for a research job"""
    await manager.send_to_job(job_id, {
        "type": "completed",
        "job_id": job_id,
        "message": "Research completed!",
        "results_summary": results_summary or {},
        "timestamp": asyncio.get_event_loop().time()
    })


async def emit_research_error(job_id: str, error: str):
    """Emit error event for a research job"""
    await manager.send_to_job(job_id, {
        "type": "error",
        "job_id": job_id,
        "error": error,
        "timestamp": asyncio.get_event_loop().time()
    })


async def emit_research_started(job_id: str, preferences: dict = None):
    """Emit started event for a research job"""
    await manager.send_to_job(job_id, {
        "type": "started",
        "job_id": job_id,
        "preferences": preferences or {},
        "message": "Research started",
        "timestamp": asyncio.get_event_loop().time()
    })


# Export the manager for use in other modules
__all__ = [
    'router',
    'manager',
    'emit_research_progress',
    'emit_research_completed',
    'emit_research_error',
    'emit_research_started'
]
