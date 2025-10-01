"""
Agent Server Implementation

This module implements HTTP servers for remote agents to handle
A2A protocol requests and provide real-time updates.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from a2a_protocol.protocol_handler import A2AProtocolHandler
from a2a_protocol.message_schema import (
    TaskRequest, TaskResponse, TaskStatus, AnalysisResult
)
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentServer:
    """
    HTTP server for remote agents
    
    Handles A2A protocol requests and provides real-time updates
    via Server-Sent Events.
    """
    
    def __init__(self, agent, port: int = 5001, host: str = "localhost"):
        """
        Initialize agent server
        
        Args:
            agent: Remote agent instance
            port: Port for the HTTP server
            host: Host for the HTTP server
        """
        self.agent = agent
        self.port = port
        self.host = host
        self.app = FastAPI(
            title=f"{agent.name} Server",
            description=f"A2A Protocol Server for {agent.name}",
            version="1.0.0"
        )
        
        # Protocol handler for this agent
        self.protocol_handler = A2AProtocolHandler(agent.agent_id)
        
        # Active tasks tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # SSE heartbeat tracking
        self._last_heartbeat = time.time()
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register endpoints
        self._register_endpoints()
        
        logger.info(f"Initialized {agent.name} server on {host}:{port}")
    
    def _register_endpoints(self):
        """Register FastAPI endpoints"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "agent_id": self.agent.agent_id,
                "name": self.agent.name,
                "status": "active",
                "capabilities": [cap.name for cap in self.agent.capabilities],
                "endpoint": f"http://{self.host}:{self.port}",
                "protocol": "A2A",
                "version": "1.0.0"
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "agent_id": self.agent.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "active_tasks": len(self.active_tasks),
                "uptime": "running"
            }
        
        @self.app.get("/capabilities")
        async def get_capabilities():
            """Get agent capabilities"""
            return {
                "agent_id": self.agent.agent_id,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "parameters": cap.parameters
                    }
                    for cap in self.agent.capabilities
                ]
            }
        
        @self.app.post("/analyze")
        async def analyze_code(request: Request):
            """Handle A2A task requests"""
            try:
                # Parse JSON-RPC request
                request_data = await request.json()
                
                # Validate request format
                if "method" not in request_data or "params" not in request_data:
                    raise HTTPException(status_code=400, detail="Invalid JSON-RPC request")
                
                # Extract task parameters
                task_params = request_data["params"]
                task_id = request_data.get("id", f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                
                logger.info(f"Received analysis request {task_id} for {self.agent.name}")
                
                # Track active task
                self.active_tasks[task_id] = {
                    "status": TaskStatus.RUNNING,
                    "started_at": datetime.utcnow(),
                    "params": task_params
                }
                
                # Perform analysis using the agent
                try:
                    result = await self.agent.analyze_code(task_params)
                    
                    # Update task status
                    self.active_tasks[task_id]["status"] = TaskStatus.COMPLETED
                    self.active_tasks[task_id]["completed_at"] = datetime.utcnow()
                    self.active_tasks[task_id]["result"] = result
                    
                    # Create response
                    try:
                        result_data = result.dict() if hasattr(result, 'dict') else result
                    except Exception as e:
                        logger.warning(f"Failed to serialize result for task {task_id}: {e}")
                        result_data = {"error": "Failed to serialize result"}
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_id,
                        "result": result_data,
                        "status": "completed"
                    }
                    
                    logger.info(f"Completed analysis request {task_id}")
                    return JSONResponse(content=response)
                    
                except Exception as e:
                    # Update task status to failed
                    self.active_tasks[task_id]["status"] = TaskStatus.FAILED
                    self.active_tasks[task_id]["error"] = str(e)
                    self.active_tasks[task_id]["failed_at"] = datetime.utcnow()
                    
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": task_id,
                        "error": {
                            "code": -32000,
                            "message": str(e),
                            "data": {"task_id": task_id}
                        }
                    }
                    
                    logger.error(f"Analysis failed for task {task_id}: {e}")
                    return JSONResponse(content=error_response, status_code=500)
                    
            except Exception as e:
                logger.error(f"Error handling analysis request: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/tasks/{task_id}")
        async def get_task_status(task_id: str):
            """Get task status"""
            if task_id not in self.active_tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task_info = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": task_info["status"],
                "started_at": task_info["started_at"].isoformat(),
                "agent_id": self.agent.agent_id
            }
        
        @self.app.get("/tasks")
        async def get_all_tasks():
            """Get all active tasks"""
            return {
                "agent_id": self.agent.agent_id,
                "active_tasks": len(self.active_tasks),
                "tasks": [
                    {
                        "task_id": task_id,
                        "status": task_info["status"],
                        "started_at": task_info["started_at"].isoformat()
                    }
                    for task_id, task_info in self.active_tasks.items()
                ]
            }
        
        @self.app.get("/events")
        async def stream_events():
            """Stream real-time events via Server-Sent Events"""
            
            async def event_generator():
                """Generate SSE events"""
                try:
                    # Send initial connection event
                    try:
                        yield f"data: {json.dumps({'type': 'connected', 'agent_id': self.agent.agent_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    except Exception as e:
                        logger.error(f"Error sending initial SSE event: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to initialize connection'})}\n\n"
                    
                    # Track previous task count
                    previous_task_count = len(self.active_tasks)
                    
                    while True:
                        # Check for new tasks or status changes
                        current_task_count = len(self.active_tasks)
                        
                        if current_task_count != previous_task_count:
                            # Send task count update
                            try:
                                yield f"data: {json.dumps({'type': 'task_count_update', 'count': current_task_count, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                                previous_task_count = current_task_count
                            except Exception as e:
                                logger.error(f"Error sending task count update: {e}")
                                continue
                        
                        # Check for completed tasks
                        for task_id, task_info in list(self.active_tasks.items()):
                            try:
                                if (task_info.get("status") == TaskStatus.COMPLETED and 
                                    "event_sent" not in task_info):
                                    # Send completion event
                                    yield f"data: {json.dumps({'type': 'task_completed', 'task_id': task_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                                    task_info["event_sent"] = True
                                elif (task_info.get("status") == TaskStatus.FAILED and 
                                      "error_event_sent" not in task_info):
                                    # Send error event
                                    yield f"data: {json.dumps({'type': 'task_failed', 'task_id': task_id, 'error': task_info.get('error', 'Unknown error'), 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                                    task_info["error_event_sent"] = True
                            except Exception as e:
                                logger.error(f"Error processing task {task_id} event: {e}")
                                continue
                        
                                # Send heartbeat every 30 seconds
                        current_time = time.time()
                        if current_time - self._last_heartbeat >= 30:
                            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                            self._last_heartbeat = current_time
                        
                        # Wait before next check
                        await asyncio.sleep(5)
                        
                except asyncio.CancelledError:
                    logger.info("SSE connection cancelled")
                    return  # Exit the generator function
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*"
                }
            )
    
    async def start(self):
        """Start the agent server"""
        try:
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            logger.info(f"Starting {self.agent.name} server on {self.host}:{self.port}")
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start agent server: {e}")
            raise
    
    async def stop(self):
        """Stop the agent server"""
        logger.info(f"Stopping {self.agent.name} server")
        # Cleanup logic here if needed


def create_agent_server(agent, port: int) -> AgentServer:
    """
    Factory function to create an agent server
    
    Args:
        agent: Remote agent instance
        port: Port for the server
        
    Returns:
        AgentServer instance
    """
    return AgentServer(agent, port)
