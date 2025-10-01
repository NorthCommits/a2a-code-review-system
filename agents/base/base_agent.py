"""
Base Agent Class

This module defines the abstract base class for all A2A agents.
Provides common functionality and interface definitions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from a2a_protocol.message_schema import TaskStatus, TaskParameters, AnalysisResult
from utils.logger import A2ALogger


class BaseAgent(ABC):
    """
    Abstract base class for all A2A agents
    
    Provides common functionality for agent lifecycle management,
    task tracking, and A2A protocol compliance.
    """
    
    def __init__(self, agent_id: str, agent_type: str, name: str):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (coordinator, remote, internal)
            name: Human-readable agent name
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.logger = A2ALogger(agent_id, agent_type)
        self.status = "initialized"
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        self.logger.info(f"Initialized {agent_type} agent: {name}")
    
    @abstractmethod
    async def start(self) -> bool:
        """
        Start the agent
        
        Returns:
            True if startup was successful
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop the agent
        
        Returns:
            True if shutdown was successful
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status information
        
        Returns:
            Agent status dictionary
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "status": self.status,
            "active_tasks": len(self.active_tasks),
            "total_tasks": len(self.task_history),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    def create_task(self, task_type: str, parameters: Dict[str, Any]) -> str:
        """
        Create a new task
        
        Args:
            task_type: Type of task
            parameters: Task parameters
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task_info = {
            "task_id": task_id,
            "task_type": task_type,
            "parameters": parameters,
            "status": TaskStatus.PENDING,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        self.active_tasks[task_id] = task_info
        self.task_history.append(task_info.copy())
        
        self.logger.log_task_start(task_id, task_type)
        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """
        Update task status
        
        Args:
            task_id: Task identifier
            status: New task status
            result: Optional task result
            error: Optional error message
        """
        if task_id not in self.active_tasks:
            self.logger.warning(f"Task {task_id} not found in active tasks")
            return
        
        task_info = self.active_tasks[task_id]
        task_info["status"] = status
        task_info["last_updated"] = datetime.utcnow()
        
        if status == TaskStatus.RUNNING:
            task_info["started_at"] = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task_info["completed_at"] = datetime.utcnow()
            
            # Move to history if completed
            if status == TaskStatus.COMPLETED:
                task_info["result"] = result
                self.logger.log_task_complete(task_id, 0.0)  # Duration would be calculated
            else:
                task_info["error"] = error
                self.logger.log_task_error(task_id, error or "Unknown error")
            
            # Keep in active tasks for a while, then move to history
            # In a real implementation, you might want to implement cleanup logic
        
        self.last_activity = datetime.utcnow()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status information or None if not found
        """
        return self.active_tasks.get(task_id)
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks"""
        return self.active_tasks.copy()
    
    def get_task_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get task history
        
        Args:
            limit: Optional limit on number of tasks to return
            
        Returns:
            List of historical tasks
        """
        history = self.task_history.copy()
        if limit:
            history = history[-limit:]
        return history
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled
        """
        if task_id not in self.active_tasks:
            return False
        
        task_info = self.active_tasks[task_id]
        if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        self.update_task_status(task_id, TaskStatus.CANCELLED, error="Cancelled by user")
        self.logger.info(f"Cancelled task {task_id}")
        return True
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Cleanup old completed tasks
        
        Args:
            max_age_hours: Maximum age of tasks to keep in active list
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = []
        for task_id, task_info in self.active_tasks.items():
            if (task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task_info.get("completed_at") and task_info["completed_at"] < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def validate_task_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate task parameters
        
        Args:
            parameters: Task parameters to validate
            
        Returns:
            True if parameters are valid
        """
        # Basic validation - can be overridden by subclasses
        if not isinstance(parameters, dict):
            return False
        
        # Check for required parameters
        required_params = ["code"]
        for param in required_params:
            if param not in parameters:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        
        return True
    
    def create_analysis_result(
        self, 
        task_id: str, 
        status: TaskStatus,
        observations: Optional[List[Dict[str, Any]]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        suggestions: Optional[List[Dict[str, Any]]] = None,
        corrected_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Create standardized analysis result
        
        Args:
            task_id: Task identifier
            status: Analysis status
            observations: List of observations
            errors: List of errors
            suggestions: List of suggestions
            corrected_code: Corrected code
            metadata: Additional metadata
            
        Returns:
            Analysis result
        """
        return AnalysisResult(
            agent_id=self.agent_id,
            task_id=task_id,
            status=status,
            observations=observations or [],
            errors=errors or [],
            suggestions=suggestions or [],
            corrected_code=corrected_code,
            metadata=metadata or {}
        )
    
    def update_status(self, status: str):
        """
        Update agent status
        
        Args:
            status: New agent status
        """
        old_status = self.status
        self.status = status
        self.last_activity = datetime.utcnow()
        
        self.logger.info(f"Agent status changed from {old_status} to {status}")
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """
        Get agent capabilities
        
        Returns:
            List of capability dictionaries
        """
        # Override in subclasses to provide specific capabilities
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Health status information
        """
        return {
            "status": "healthy" if self.status == "active" else "unhealthy",
            "agent_id": self.agent_id,
            "uptime": (datetime.utcnow() - self.created_at).total_seconds(),
            "active_tasks": len(self.active_tasks),
            "last_activity": self.last_activity.isoformat()
        }
