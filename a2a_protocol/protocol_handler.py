"""
A2A Protocol Handler

This module implements the core A2A protocol handler using JSON-RPC 2.0
for agent-to-agent communication.
"""

import json
import uuid
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime
import httpx
from .message_schema import (
    A2AMessage, TaskRequest, TaskResponse, TaskStatusQuery, 
    TaskCancellation, Notification, TaskStatus, AnalysisResult
)
from utils.logger import get_logger

logger = get_logger(__name__)


class A2AProtocolError(Exception):
    """Custom exception for A2A protocol errors"""
    pass


class A2AProtocolHandler:
    """
    Core A2A protocol handler implementing JSON-RPC 2.0
    
    Handles communication between agents using the A2A protocol
    with support for synchronous and asynchronous operations.
    """
    
    def __init__(self, agent_id: str, timeout: int = 30):
        """
        Initialize A2A protocol handler
        
        Args:
            agent_id: Unique identifier for this agent
            timeout: Request timeout in seconds
        """
        self.agent_id = agent_id
        self.timeout = timeout
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def send_task_request(
        self, 
        target_agent_endpoint: str, 
        task_params: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> TaskResponse:
        """
        Send a task request to a remote agent
        
        Args:
            target_agent_endpoint: Endpoint URL of the target agent
            task_params: Task parameters
            task_id: Optional task ID, generates one if not provided
            
        Returns:
            TaskResponse from the remote agent
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
            
        request = TaskRequest(
            id=task_id,
            method="analyze_code",
            params=task_params
        )
        
        try:
            logger.info(f"Sending task request {task_id} to {target_agent_endpoint}")
            
            response = await self.client.post(
                target_agent_endpoint,
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            response_data = response.json()
            task_response = TaskResponse(**response_data)
            
            # Track active task
            self.active_tasks[task_id] = {
                "status": TaskStatus.RUNNING,
                "endpoint": target_agent_endpoint,
                "created_at": datetime.utcnow(),
                "response": task_response
            }
            
            logger.info(f"Received response for task {task_id}")
            return task_response
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending task request {task_id}: {e}")
            raise A2AProtocolError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error sending task request {task_id}: {e}")
            raise A2AProtocolError(f"Request failed: {e}")
    
    async def query_task_status(
        self, 
        target_agent_endpoint: str, 
        task_id: str
    ) -> Dict[str, Any]:
        """
        Query the status of a task
        
        Args:
            target_agent_endpoint: Endpoint URL of the target agent
            task_id: Task ID to query
            
        Returns:
            Task status information
        """
        request = TaskStatusQuery(
            id=str(uuid.uuid4()),
            method="get_task_status",
            params={"task_id": task_id}
        )
        
        try:
            response = await self.client.post(
                target_agent_endpoint,
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            response_data = response.json()
            return response_data.get("result", {})
            
        except Exception as e:
            logger.error(f"Error querying task status {task_id}: {e}")
            raise A2AProtocolError(f"Status query failed: {e}")
    
    async def cancel_task(
        self, 
        target_agent_endpoint: str, 
        task_id: str
    ) -> bool:
        """
        Cancel a running task
        
        Args:
            target_agent_endpoint: Endpoint URL of the target agent
            task_id: Task ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        request = TaskCancellation(
            id=str(uuid.uuid4()),
            method="cancel_task",
            params={"task_id": task_id}
        )
        
        try:
            response = await self.client.post(
                target_agent_endpoint,
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Update local task status
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = TaskStatus.CANCELLED
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def create_notification(
        self, 
        method: str, 
        params: Dict[str, Any]
    ) -> Notification:
        """
        Create a notification message
        
        Args:
            method: Notification method name
            params: Notification parameters
            
        Returns:
            Notification message
        """
        return Notification(method=method, params=params)
    
    def parse_message(self, message_data: Dict[str, Any]) -> Union[A2AMessage, Notification]:
        """
        Parse incoming A2A message
        
        Args:
            message_data: Raw message data
            
        Returns:
            Parsed A2A message or notification
        """
        try:
            if "id" in message_data:
                # This is a request/response message
                return A2AMessage(**message_data)
            else:
                # This is a notification
                return Notification(**message_data)
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            raise A2AProtocolError(f"Message parsing failed: {e}")
    
    def create_error_response(
        self, 
        request_id: Optional[Union[str, int]], 
        error_code: int, 
        error_message: str
    ) -> TaskResponse:
        """
        Create an error response
        
        Args:
            request_id: Original request ID
            error_code: Error code
            error_message: Error message
            
        Returns:
            Error response message
        """
        return TaskResponse(
            id=request_id,
            error={
                "code": error_code,
                "message": error_message
            }
        )
    
    def create_success_response(
        self, 
        request_id: Optional[Union[str, int]], 
        result: Dict[str, Any]
    ) -> TaskResponse:
        """
        Create a success response
        
        Args:
            request_id: Original request ID
            result: Response result data
            
        Returns:
            Success response message
        """
        return TaskResponse(
            id=request_id,
            result=result
        )
    
    async def close(self):
        """Close the protocol handler and cleanup resources"""
        await self.client.aclose()
        self.active_tasks.clear()
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks"""
        return self.active_tasks.copy()
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update local task status"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = status
            self.active_tasks[task_id]["updated_at"] = datetime.utcnow()
