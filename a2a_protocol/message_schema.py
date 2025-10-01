"""
A2A Protocol Message Schema Definitions

This module defines the message schemas for the Agent-to-Agent (A2A) protocol
based on JSON-RPC 2.0 specification.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """A2A message types"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_STATUS_QUERY = "task_status_query"
    TASK_CANCELLATION = "task_cancellation"
    NOTIFICATION = "notification"


class A2AMessage(BaseModel):
    """Base A2A message structure following JSON-RPC 2.0"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID for correlation")
    method: str = Field(description="A2A method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")


class TaskRequest(A2AMessage):
    """Task request message for remote agents"""
    method: str = Field(default="analyze_code", description="Analysis method")
    params: Dict[str, Any] = Field(description="Task parameters including code and analysis type")


class TaskResponse(BaseModel):
    """Task response message from remote agents"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(description="Request ID for correlation")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task results")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")


class TaskStatusQuery(A2AMessage):
    """Task status query message"""
    method: str = Field(default="get_task_status", description="Status query method")
    params: Dict[str, Any] = Field(description="Task ID for status query")


class TaskCancellation(A2AMessage):
    """Task cancellation message"""
    method: str = Field(default="cancel_task", description="Cancellation method")
    params: Dict[str, Any] = Field(description="Task ID for cancellation")


class Notification(BaseModel):
    """Notification message for async updates"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(description="Notification method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Notification parameters")


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str = Field(description="Capability name")
    description: str = Field(description="Capability description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Required parameters")


class AgentInfo(BaseModel):
    """Agent information for registry"""
    agent_id: str = Field(description="Unique agent identifier")
    name: str = Field(description="Agent name")
    version: str = Field(description="Agent version")
    capabilities: List[AgentCapability] = Field(description="Agent capabilities")
    endpoint: str = Field(description="Agent endpoint URL")
    status: str = Field(default="active", description="Agent status")
    health_check_endpoint: Optional[str] = Field(default=None, description="Health check endpoint")


class AnalysisResult(BaseModel):
    """Analysis result structure"""
    agent_id: str = Field(description="Agent that performed the analysis")
    task_id: str = Field(description="Task identifier")
    status: TaskStatus = Field(description="Analysis status")
    observations: List[Dict[str, Any]] = Field(default_factory=list, description="Analysis observations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Identified errors")
    suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="Improvement suggestions")
    corrected_code: Optional[str] = Field(default=None, description="Corrected code version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TaskParameters(BaseModel):
    """Standard task parameters"""
    code: str = Field(description="Code to analyze")
    language: str = Field(default="python", description="Programming language")
    task_id: str = Field(description="Unique task identifier")
    options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")
