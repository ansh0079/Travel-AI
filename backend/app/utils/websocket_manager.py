"""
WebSocket Connection Manager
Manages WebSocket connections and job subscriptions
"""

from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime


class ConnectionManager:
    """Manage WebSocket connections and job subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.job_subscriptions: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        # Also remove from job subscriptions
        for job_id, connections in list(self.job_subscriptions.items()):
            connections.discard(websocket)
            if not connections:
                del self.job_subscriptions[job_id]
    
    async def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        """Subscribe a WebSocket to job updates"""
        if job_id not in self.job_subscriptions:
            self.job_subscriptions[job_id] = set()
        self.job_subscriptions[job_id].add(websocket)
    
    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str):
        """Unsubscribe a WebSocket from job updates"""
        if job_id in self.job_subscriptions:
            self.job_subscriptions[job_id].discard(websocket)
            if not self.job_subscriptions[job_id]:
                del self.job_subscriptions[job_id]
    
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Broadcast a message to all WebSockets subscribed to a job"""
        if job_id not in self.job_subscriptions:
            return
        
        message["timestamp"] = datetime.now().isoformat()
        disconnected = []
        
        for connection in self.job_subscriptions[job_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.job_subscriptions[job_id].discard(conn)
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client"""
        if client_id not in self.active_connections:
            return
        
        message["timestamp"] = datetime.now().isoformat()
        disconnected = []
        
        for connection in self.active_connections[client_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections[client_id].discard(conn)
    
    async def ping_all(self):
        """Keep connections alive with periodic pings"""
        while True:
            await asyncio.sleep(30)  # Ping every 30 seconds
            
            for client_id, connections in list(self.active_connections.items()):
                disconnected = []
                for conn in connections:
                    try:
                        await conn.send_json({"type": "ping"})
                    except Exception:
                        disconnected.append(conn)
                
                # Clean up
                for conn in disconnected:
                    connections.discard(conn)
                
                if not connections:
                    del self.active_connections[client_id]


# Global connection manager instance
connection_manager = ConnectionManager()
