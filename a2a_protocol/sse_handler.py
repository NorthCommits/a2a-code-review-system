"""
A2A Server-Sent Events (SSE) Handler

This module implements Server-Sent Events for real-time streaming
updates in the A2A protocol.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Set, AsyncGenerator
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from .message_schema import Notification, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class SSEError(Exception):
    """Custom exception for SSE-related errors"""
    pass


class A2ASSEHandler:
    """
    Handles Server-Sent Events for real-time streaming updates
    
    Provides real-time communication channel for task updates
    and notifications in the A2A protocol.
    """
    
    def __init__(self, app: FastAPI, sse_path: str = "/sse"):
        """
        Initialize A2A SSE handler
        
        Args:
            app: FastAPI application instance
            sse_path: Path for SSE endpoint
        """
        self.app = app
        self.sse_path = sse_path
        self.active_connections: Set[str] = set()
        self.event_queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, Set[str]] = {}  # event_type -> set of connection_ids
        
        # Register SSE endpoints
        self.app.get(f"{sse_path}/stream")(self.stream_events)
        self.app.post(f"{sse_path}/subscribe")(self.subscribe_to_events)
        self.app.post(f"{sse_path}/unsubscribe")(self.unsubscribe_from_events)
    
    async def stream_events(self, request: Request, connection_id: Optional[str] = None):
        """
        Stream events via Server-Sent Events
        
        Args:
            request: FastAPI request object
            connection_id: Optional connection identifier
            
        Returns:
            Streaming response with events
        """
        if connection_id is None:
            connection_id = f"conn_{datetime.utcnow().timestamp()}"
        
        self.active_connections.add(connection_id)
        self.event_queues[connection_id] = asyncio.Queue()
        
        logger.info(f"SSE connection established: {connection_id}")
        
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                # Send connection established event
                yield self._format_sse_event("connected", {"connection_id": connection_id})
                
                while True:
                    try:
                        # Check if client disconnected
                        if await request.is_disconnected():
                            break
                        
                        # Wait for events with timeout
                        try:
                            event_data = await asyncio.wait_for(
                                self.event_queues[connection_id].get(),
                                timeout=30.0
                            )
                            yield self._format_sse_event("message", event_data)
                        except asyncio.TimeoutError:
                            # Send keepalive ping
                            yield self._format_sse_event("ping", {"timestamp": datetime.utcnow().isoformat()})
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error in SSE stream for {connection_id}: {e}")
                        yield self._format_sse_event("error", {"error": str(e)})
                        break
                        
            except Exception as e:
                logger.error(f"SSE stream error for {connection_id}: {e}")
                yield self._format_sse_event("error", {"error": str(e)})
            finally:
                # Cleanup connection
                self._cleanup_connection(connection_id)
        
        return EventSourceResponse(event_generator())
    
    async def subscribe_to_events(self, request: Request):
        """Subscribe to specific event types"""
        try:
            data = await request.json()
            connection_id = data.get("connection_id")
            event_types = data.get("event_types", [])
            
            if not connection_id:
                return {"error": "Missing connection_id"}
            
            if connection_id not in self.active_connections:
                return {"error": "Connection not found"}
            
            # Subscribe to event types
            for event_type in event_types:
                if event_type not in self.subscribers:
                    self.subscribers[event_type] = set()
                self.subscribers[event_type].add(connection_id)
            
            logger.info(f"Connection {connection_id} subscribed to events: {event_types}")
            return {"status": "success", "subscribed_to": event_types}
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return {"error": str(e)}
    
    async def unsubscribe_from_events(self, request: Request):
        """Unsubscribe from specific event types"""
        try:
            data = await request.json()
            connection_id = data.get("connection_id")
            event_types = data.get("event_types", [])
            
            if not connection_id:
                return {"error": "Missing connection_id"}
            
            # Unsubscribe from event types
            for event_type in event_types:
                if event_type in self.subscribers:
                    self.subscribers[event_type].discard(connection_id)
            
            logger.info(f"Connection {connection_id} unsubscribed from events: {event_types}")
            return {"status": "success", "unsubscribed_from": event_types}
            
        except Exception as e:
            logger.error(f"Error unsubscribing from events: {e}")
            return {"error": str(e)}
    
    async def broadcast_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Broadcast event to all subscribers
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        if event_type not in self.subscribers:
            return
        
        message = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all subscribers of this event type
        for connection_id in self.subscribers[event_type].copy():
            if connection_id in self.active_connections:
                try:
                    await self.event_queues[connection_id].put(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    self._cleanup_connection(connection_id)
    
    async def send_to_connection(
        self, 
        connection_id: str, 
        event_type: str, 
        event_data: Dict[str, Any]
    ):
        """
        Send event to specific connection
        
        Args:
            connection_id: Target connection ID
            event_type: Type of event
            event_data: Event data
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found")
            return
        
        message = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.event_queues[connection_id].put(message)
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            self._cleanup_connection(connection_id)
    
    async def broadcast_task_update(
        self, 
        task_id: str, 
        status: TaskStatus, 
        result: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast task update event
        
        Args:
            task_id: Task identifier
            status: Task status
            result: Optional task result
        """
        event_data = {
            "task_id": task_id,
            "status": status.value,
            "result": result
        }
        
        await self.broadcast_event("task_update", event_data)
    
    async def broadcast_task_completion(
        self, 
        task_id: str, 
        result: Dict[str, Any]
    ):
        """
        Broadcast task completion event
        
        Args:
            task_id: Task identifier
            result: Task result
        """
        await self.broadcast_task_update(task_id, TaskStatus.COMPLETED, result)
    
    async def broadcast_task_error(
        self, 
        task_id: str, 
        error: Dict[str, Any]
    ):
        """
        Broadcast task error event
        
        Args:
            task_id: Task identifier
            error: Error information
        """
        event_data = {
            "task_id": task_id,
            "status": TaskStatus.FAILED.value,
            "error": error
        }
        
        await self.broadcast_event("task_error", event_data)
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Format data as SSE event
        
        Args:
            event_type: Event type
            data: Event data
            
        Returns:
            Formatted SSE event string
        """
        event_json = json.dumps(data)
        return f"event: {event_type}\ndata: {event_json}\n\n"
    
    def _cleanup_connection(self, connection_id: str):
        """
        Cleanup connection resources
        
        Args:
            connection_id: Connection identifier
        """
        # Remove from active connections
        self.active_connections.discard(connection_id)
        
        # Remove from event queues
        if connection_id in self.event_queues:
            del self.event_queues[connection_id]
        
        # Remove from all subscriber lists
        for event_type in self.subscribers:
            self.subscribers[event_type].discard(connection_id)
        
        logger.info(f"Cleaned up SSE connection: {connection_id}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get SSE connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_event_types": len(self.subscribers),
            "subscribers_per_type": {
                event_type: len(subscribers) 
                for event_type, subscribers in self.subscribers.items()
            }
        }
    
    async def close_all_connections(self):
        """Close all active SSE connections"""
        for connection_id in list(self.active_connections):
            self._cleanup_connection(connection_id)
        
        logger.info("All SSE connections closed")
