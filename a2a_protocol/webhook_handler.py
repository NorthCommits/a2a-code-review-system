"""
A2A Webhook Handler

This module handles webhook-based asynchronous notifications
for the A2A protocol.
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from .message_schema import Notification, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class WebhookError(Exception):
    """Custom exception for webhook-related errors"""
    pass


class A2AWebhookHandler:
    """
    Handles webhook-based asynchronous notifications for A2A protocol
    
    Manages webhook endpoints for receiving task updates and notifications
    from remote agents.
    """
    
    def __init__(self, webhook_port: int = 8080, webhook_path: str = "/webhook"):
        """
        Initialize A2A webhook handler
        
        Args:
            webhook_port: Port for webhook server
            webhook_path: Path for webhook endpoint
        """
        self.webhook_port = webhook_port
        self.webhook_path = webhook_path
        self.app = FastAPI(title="A2A Webhook Handler")
        self.notification_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self.server = None
        
        # Register webhook endpoint
        self.app.post(f"{webhook_path}/task_update")(self.handle_task_update)
        self.app.post(f"{webhook_path}/notification")(self.handle_notification)
        self.app.get(f"{webhook_path}/health")(self.health_check)
    
    async def handle_task_update(self, request: Request) -> JSONResponse:
        """
        Handle task update webhook
        
        Args:
            request: FastAPI request object
            
        Returns:
            JSON response
        """
        try:
            data = await request.json()
            logger.info(f"Received task update webhook: {data}")
            
            # Validate webhook data
            if "task_id" not in data:
                raise HTTPException(status_code=400, detail="Missing task_id")
            
            task_id = data["task_id"]
            status = data.get("status")
            
            # Update local task tracking
            await self._update_task_status(task_id, status, data)
            
            # Call registered handlers
            if "task_update" in self.notification_handlers:
                await self.notification_handlers["task_update"](data)
            
            return JSONResponse({"status": "success", "message": "Task update processed"})
            
        except Exception as e:
            logger.error(f"Error handling task update webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_notification(self, request: Request) -> JSONResponse:
        """
        Handle general notification webhook
        
        Args:
            request: FastAPI request object
            
        Returns:
            JSON response
        """
        try:
            data = await request.json()
            logger.info(f"Received notification webhook: {data}")
            
            # Parse as A2A notification
            notification = Notification(**data)
            
            # Call registered handlers
            handler_key = f"notification_{notification.method}"
            if handler_key in self.notification_handlers:
                await self.notification_handlers[handler_key](data)
            elif "notification" in self.notification_handlers:
                await self.notification_handlers["notification"](data)
            
            return JSONResponse({"status": "success", "message": "Notification processed"})
            
        except Exception as e:
            logger.error(f"Error handling notification webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def health_check(self) -> JSONResponse:
        """
        Health check endpoint
        
        Returns:
            Health status
        """
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "A2A Webhook Handler"
        })
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: Optional[str], 
        data: Dict[str, Any]
    ):
        """
        Update local task status tracking
        
        Args:
            task_id: Task identifier
            status: New task status
            data: Additional task data
        """
        # This would integrate with the main task tracking system
        # For now, just log the update
        logger.info(f"Task {task_id} status updated to {status}")
        
        # Store additional metadata
        if "result" in data:
            logger.debug(f"Task {task_id} result: {data['result']}")
        
        if "error" in data:
            logger.warning(f"Task {task_id} error: {data['error']}")
    
    def register_handler(
        self, 
        event_type: str, 
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Register a webhook event handler
        
        Args:
            event_type: Type of event to handle
            handler: Async handler function
        """
        self.notification_handlers[event_type] = handler
        logger.info(f"Registered webhook handler for event type: {event_type}")
    
    def unregister_handler(self, event_type: str):
        """
        Unregister a webhook event handler
        
        Args:
            event_type: Type of event to unregister
        """
        if event_type in self.notification_handlers:
            del self.notification_handlers[event_type]
            logger.info(f"Unregistered webhook handler for event type: {event_type}")
    
    async def start_server(self):
        """Start the webhook server"""
        import uvicorn
        
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.webhook_port,
            log_level="info"
        )
        self.server = uvicorn.Server(config)
        
        logger.info(f"Starting A2A webhook server on port {self.webhook_port}")
        await self.server.serve()
    
    async def stop_server(self):
        """Stop the webhook server"""
        if self.server:
            logger.info("Stopping A2A webhook server")
            self.server.should_exit = True
    
    def get_webhook_url(self, base_url: str = "http://localhost") -> str:
        """
        Get the webhook URL for this handler
        
        Args:
            base_url: Base URL for webhook
            
        Returns:
            Complete webhook URL
        """
        return f"{base_url}:{self.webhook_port}{self.webhook_path}"
    
    def create_task_update_notification(
        self, 
        task_id: str, 
        status: TaskStatus, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a task update notification
        
        Args:
            task_id: Task identifier
            status: New task status
            result: Optional task result
            error: Optional error information
            
        Returns:
            Notification data
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "task_update",
            "params": {
                "task_id": task_id,
                "status": status.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if result:
            notification["params"]["result"] = result
        
        if error:
            notification["params"]["error"] = error
        
        return notification
    
    def create_completion_notification(
        self, 
        task_id: str, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a task completion notification
        
        Args:
            task_id: Task identifier
            result: Task result data
            
        Returns:
            Completion notification data
        """
        return self.create_task_update_notification(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=result
        )
    
    def create_error_notification(
        self, 
        task_id: str, 
        error: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a task error notification
        
        Args:
            task_id: Task identifier
            error: Error information
            
        Returns:
            Error notification data
        """
        return self.create_task_update_notification(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error
        )
    
    async def send_webhook(
        self, 
        target_url: str, 
        notification_data: Dict[str, Any]
    ) -> bool:
        """
        Send webhook notification to target URL
        
        Args:
            target_url: Target webhook URL
            notification_data: Notification data
            
        Returns:
            True if webhook was sent successfully
        """
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    target_url,
                    json=notification_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                response.raise_for_status()
                
                logger.debug(f"Webhook sent successfully to {target_url}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send webhook to {target_url}: {e}")
            return False
