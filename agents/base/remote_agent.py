"""
Remote Agent Base Class

This module defines the base class for remote agents that receive
and process tasks via the A2A protocol.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from abc import abstractmethod
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from .base_agent import BaseAgent
from a2a_protocol.message_schema import (
    TaskRequest, TaskResponse, TaskStatus, AnalysisResult, 
    AgentInfo, AgentCapability
)
from utils.logger import A2ALogger


class RemoteAgent(BaseAgent):
    """
    Base class for remote agents that process tasks from client agents
    
    Provides HTTP endpoints for receiving A2A protocol messages,
    task processing, and response handling.
    """
    
    def __init__(
        self, 
        agent_id: str, 
        name: str,
        capabilities: List[AgentCapability],
        port: int = 5000
    ):
        """
        Initialize remote agent
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
            capabilities: List of agent capabilities
            port: Port for HTTP server
        """
        super().__init__(agent_id, "remote", name)
        self.port = port
        self.capabilities = capabilities
        self.logger = A2ALogger(agent_id, "remote")
        
        # Create FastAPI app
        self.app = FastAPI(
            title=f"A2A {name}",
            description=f"Remote agent for {name}",
            version="1.0.0"
        )
        
        # Register endpoints
        self._register_endpoints()
        
        self.logger.info(f"Initialized remote agent: {name}")
    
    def _register_endpoints(self):
        """Register FastAPI endpoints for A2A protocol"""
        
        @self.app.post("/analyze")
        async def analyze_code(request: Request):
            """Main analysis endpoint"""
            try:
                data = await request.json()
                task_request = TaskRequest(**data)
                
                self.logger.log_protocol_message("task_request", "client", "incoming")
                
                # Process the task
                result = await self.process_task(task_request)
                
                # Create response
                response = TaskResponse(
                    id=task_request.id,
                    result=result.dict() if result else None
                )
                
                return response.dict()
                
            except Exception as e:
                self.logger.error(f"Error processing analysis request: {e}")
                
                # Create error response
                error_response = TaskResponse(
                    id=getattr(task_request, 'id', None) if 'task_request' in locals() else None,
                    error={
                        "code": -1,
                        "message": str(e)
                    }
                )
                
                return error_response.dict()
        
        @self.app.get("/task_status/{task_id}")
        async def get_task_status(task_id: str):
            """Get task status endpoint"""
            try:
                task_info = self.get_task_status(task_id)
                
                if not task_info:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                return {
                    "task_id": task_id,
                    "status": task_info["status"].value,
                    "created_at": task_info["created_at"].isoformat(),
                    "started_at": task_info["started_at"].isoformat() if task_info["started_at"] else None,
                    "completed_at": task_info["completed_at"].isoformat() if task_info["completed_at"] else None
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting task status for {task_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/cancel/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel task endpoint"""
            try:
                success = self.cancel_task(task_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
                
                return {"message": f"Task {task_id} cancelled successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error cancelling task {task_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                health_info = self.health_check()
                return health_info
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                return {"status": "unhealthy", "error": str(e)}
        
        @self.app.get("/capabilities")
        async def get_capabilities():
            """Get agent capabilities"""
            try:
                capabilities = self.get_capabilities()
                return {"capabilities": capabilities}
                
            except Exception as e:
                self.logger.error(f"Error getting capabilities: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/status")
        async def get_agent_status():
            """Get agent status"""
            try:
                status_info = self.get_status()
                return status_info
                
            except Exception as e:
                self.logger.error(f"Error getting agent status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def start(self) -> bool:
        """
        Start the remote agent
        
        Returns:
            True if startup was successful
        """
        try:
            self.update_status("starting")
            
            # Start the HTTP server
            import uvicorn
            
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info"
            )
            self.server = uvicorn.Server(config)
            
            # Start server in background
            self.server_task = asyncio.create_task(self.server.serve())
            
            self.update_status("active")
            self.logger.info(f"Remote agent started on port {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start remote agent: {e}")
            self.update_status("failed")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the remote agent
        
        Returns:
            True if shutdown was successful
        """
        try:
            self.update_status("stopping")
            
            # Stop the HTTP server
            if hasattr(self, 'server_task'):
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel any running tasks
            for task_id in list(self.active_tasks.keys()):
                self.cancel_task(task_id)
            
            self.update_status("stopped")
            self.logger.info("Remote agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop remote agent: {e}")
            return False
    
    async def process_task(self, task_request: TaskRequest) -> Optional[AnalysisResult]:
        """
        Process an incoming task request
        
        Args:
            task_request: Task request from client
            
        Returns:
            Analysis result or None if processing failed
        """
        try:
            task_id = task_request.id or str(uuid.uuid4())
            task_params = task_request.params
            
            # Validate task parameters
            if not self.validate_task_parameters(task_params):
                raise ValueError("Invalid task parameters")
            
            # Create task
            self.create_task("analyze_code", task_params)
            self.update_task_status(task_id, TaskStatus.RUNNING)
            
            # Process the task (implemented by subclasses)
            result = await self.analyze_code(task_params)
            
            # Update task status
            if result:
                self.update_task_status(task_id, TaskStatus.COMPLETED, result=result.dict())
            else:
                self.update_task_status(task_id, TaskStatus.FAILED, error="Analysis failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing task: {e}")
            
            # Update task status
            if 'task_id' in locals():
                self.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            
            return None
    
    @abstractmethod
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code - implemented by subclasses
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Analysis result
        """
        pass
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """
        Get agent capabilities
        
        Returns:
            List of capability dictionaries
        """
        return [
            {
                "name": cap.name,
                "description": cap.description,
                "parameters": cap.parameters
            }
            for cap in self.capabilities
        ]
    
    def get_agent_info(self) -> AgentInfo:
        """
        Get agent information for registry
        
        Returns:
            Agent information
        """
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            version="1.0.0",
            capabilities=self.capabilities,
            endpoint=f"http://localhost:{self.port}/analyze",
            health_check_endpoint=f"http://localhost:{self.port}/health",
            status=self.status
        )
    
    def get_endpoint_url(self) -> str:
        """Get the agent endpoint URL"""
        return f"http://localhost:{self.port}"
    
    async def wait_for_shutdown(self):
        """Wait for server shutdown"""
        if hasattr(self, 'server_task'):
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
