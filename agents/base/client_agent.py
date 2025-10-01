"""
Client Agent Base Class

This module defines the base class for client agents (like the coordinator)
that send tasks to remote agents via the A2A protocol.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from .base_agent import BaseAgent
from a2a_protocol.protocol_handler import A2AProtocolHandler
from a2a_protocol.message_schema import TaskResponse, AnalysisResult, TaskStatus
from registry.agent_registry import AgentRegistry
from utils.logger import A2ALogger


class ClientAgent(BaseAgent):
    """
    Base class for client agents that communicate with remote agents
    
    Provides functionality for sending tasks to remote agents,
    managing responses, and aggregating results.
    """
    
    def __init__(
        self, 
        agent_id: str, 
        name: str,
        registry: Optional[AgentRegistry] = None,
        timeout: int = 30
    ):
        """
        Initialize client agent
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
            registry: Agent registry for discovery
            timeout: Request timeout in seconds
        """
        super().__init__(agent_id, "client", name)
        self.registry = registry
        self.protocol_handler = A2AProtocolHandler(agent_id, timeout)
        self.logger = A2ALogger(agent_id, "client")
        
        # Task management
        self.pending_responses: Dict[str, Dict[str, Any]] = {}
        self.response_timeout = timeout
        
        self.logger.info(f"Initialized client agent: {name}")
    
    async def start(self) -> bool:
        """
        Start the client agent
        
        Returns:
            True if startup was successful
        """
        try:
            self.update_status("starting")
            
            # Start registry health monitoring if available
            if self.registry:
                self.registry.start_health_monitoring()
            
            self.update_status("active")
            self.logger.info("Client agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start client agent: {e}")
            self.update_status("failed")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the client agent
        
        Returns:
            True if shutdown was successful
        """
        try:
            self.update_status("stopping")
            
            # Stop registry health monitoring if available
            if self.registry:
                self.registry.stop_health_monitoring()
            
            # Cancel all pending tasks
            for task_id in list(self.pending_responses.keys()):
                await self.cancel_remote_task(task_id)
            
            # Close protocol handler
            await self.protocol_handler.close()
            
            self.update_status("stopped")
            self.logger.info("Client agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop client agent: {e}")
            return False
    
    async def send_task_to_agent(
        self, 
        target_agent_id: str, 
        task_params: Dict[str, Any],
        task_type: str = "analyze_code"
    ) -> str:
        """
        Send task to a specific remote agent
        
        Args:
            target_agent_id: Target agent identifier
            task_params: Task parameters
            task_type: Type of task
            
        Returns:
            Task ID for tracking
        """
        try:
            # Get agent information from registry
            if not self.registry:
                raise Exception("No registry available for agent discovery")
            
            agent_info = self.registry.get_agent(target_agent_id)
            if not agent_info:
                raise Exception(f"Agent {target_agent_id} not found in registry")
            
            # Create local task
            task_id = self.create_task(task_type, task_params)
            
            # Send task to remote agent
            self.logger.log_protocol_message("task_request", target_agent_id, "outgoing")
            
            response = await self.protocol_handler.send_task_request(
                agent_info.endpoint,
                task_params,
                task_id
            )
            
            # Track pending response
            self.pending_responses[task_id] = {
                "target_agent_id": target_agent_id,
                "target_endpoint": agent_info.endpoint,
                "task_type": task_type,
                "sent_at": datetime.utcnow(),
                "response": response
            }
            
            # Update task status
            self.update_task_status(task_id, TaskStatus.RUNNING)
            
            self.logger.log_agent_communication(target_agent_id, "send_task", True)
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to send task to agent {target_agent_id}: {e}")
            self.logger.log_agent_communication(target_agent_id, "send_task", False)
            raise
    
    async def send_task_by_capability(
        self, 
        required_capabilities: List[str], 
        task_params: Dict[str, Any],
        task_type: str = "analyze_code"
    ) -> Optional[str]:
        """
        Send task to best available agent with required capabilities
        
        Args:
            required_capabilities: List of required capabilities
            task_params: Task parameters
            task_type: Type of task
            
        Returns:
            Task ID if successful, None otherwise
        """
        try:
            if not self.registry:
                raise Exception("No registry available for agent discovery")
            
            # Find best agent for capabilities
            best_agent = self.registry.find_best_agent(required_capabilities)
            if not best_agent:
                self.logger.warning(f"No agent found with capabilities: {required_capabilities}")
                return None
            
            # Send task to best agent
            task_id = await self.send_task_to_agent(
                best_agent.agent_id,
                task_params,
                task_type
            )
            
            self.logger.info(f"Sent task {task_id} to best agent {best_agent.agent_id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to send task by capability: {e}")
            return None
    
    async def send_tasks_to_multiple_agents(
        self, 
        agent_capability_map: Dict[str, List[str]], 
        task_params: Dict[str, Any],
        task_type: str = "analyze_code"
    ) -> Dict[str, str]:
        """
        Send tasks to multiple agents based on capability requirements
        
        Args:
            agent_capability_map: Map of agent IDs to their required capabilities
            task_params: Task parameters
            task_type: Type of task
            
        Returns:
            Dictionary mapping agent IDs to task IDs
        """
        task_ids = {}
        
        try:
            # Create tasks for each agent
            tasks = []
            for agent_id, capabilities in agent_capability_map.items():
                if self.registry and self.registry.get_agent(agent_id):
                    task = self.send_task_to_agent(agent_id, task_params, task_type)
                    tasks.append((agent_id, task))
            
            # Execute all tasks concurrently
            if tasks:
                results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
                
                for i, (agent_id, _) in enumerate(tasks):
                    result = results[i]
                    if isinstance(result, Exception):
                        self.logger.error(f"Failed to send task to {agent_id}: {result}")
                    else:
                        task_ids[agent_id] = result
            
            self.logger.info(f"Sent tasks to {len(task_ids)} agents")
            return task_ids
            
        except Exception as e:
            self.logger.error(f"Failed to send tasks to multiple agents: {e}")
            return task_ids
    
    async def get_task_result(self, task_id: str, timeout: Optional[int] = None) -> Optional[AnalysisResult]:
        """
        Get result for a completed task
        
        Args:
            task_id: Task identifier
            timeout: Optional timeout override
            
        Returns:
            Analysis result or None if not available
        """
        try:
            # Check if we have the response
            if task_id not in self.pending_responses:
                self.logger.warning(f"No pending response for task {task_id}")
                return None
            
            response_info = self.pending_responses[task_id]
            response = response_info["response"]
            
            # Check for errors in response
            if response.error:
                self.logger.error(f"Task {task_id} failed: {response.error}")
                self.update_task_status(task_id, TaskStatus.FAILED, error=str(response.error))
                return None
            
            # Extract result
            if response.result:
                result = AnalysisResult(**response.result)
                self.update_task_status(task_id, TaskStatus.COMPLETED, result=response.result)
                
                # Clean up pending response
                del self.pending_responses[task_id]
                
                return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting task result for {task_id}: {e}")
            return None
    
    async def cancel_remote_task(self, task_id: str) -> bool:
        """
        Cancel a task on the remote agent
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if cancellation was successful
        """
        try:
            if task_id not in self.pending_responses:
                return False
            
            response_info = self.pending_responses[task_id]
            target_endpoint = response_info["target_endpoint"]
            
            # Cancel task on remote agent
            success = await self.protocol_handler.cancel_task(target_endpoint, task_id)
            
            if success:
                self.update_task_status(task_id, TaskStatus.CANCELLED)
                del self.pending_responses[task_id]
                self.logger.info(f"Cancelled remote task {task_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to cancel remote task {task_id}: {e}")
            return False
    
    async def query_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Query task status from remote agent
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status information or None
        """
        try:
            if task_id not in self.pending_responses:
                return None
            
            response_info = self.pending_responses[task_id]
            target_endpoint = response_info["target_endpoint"]
            
            status = await self.protocol_handler.query_task_status(target_endpoint, task_id)
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to query task status for {task_id}: {e}")
            return None
    
    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending task responses"""
        return self.pending_responses.copy()
    
    async def wait_for_completion(
        self, 
        task_ids: List[str], 
        timeout: Optional[int] = None
    ) -> Dict[str, AnalysisResult]:
        """
        Wait for multiple tasks to complete
        
        Args:
            task_ids: List of task IDs to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary mapping task IDs to results
        """
        results = {}
        
        try:
            # Wait for all tasks to complete
            for task_id in task_ids:
                result = await self.get_task_result(task_id, timeout)
                if result:
                    results[task_id] = result
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error waiting for task completion: {e}")
            return results
