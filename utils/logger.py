"""
Logging Utility

This module provides centralized logging configuration for the A2A Code Review System.
"""

import logging
import sys
from typing import Optional
from datetime import datetime


class A2ALogFormatter(logging.Formatter):
    """Custom log formatter for A2A system"""
    
    def format(self, record):
        # Add timestamp and system identifier
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        record.timestamp = timestamp
        record.system = "A2A-CodeReview"
        
        # Format the message
        if hasattr(record, 'agent_id'):
            return f"[{record.timestamp}] {record.system} [{record.agent_id}] {record.levelname}: {record.getMessage()}"
        else:
            return f"[{record.timestamp}] {record.system} {record.levelname}: {record.getMessage()}"


def get_logger(name: str, agent_id: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Get a configured logger for the A2A system
    
    Args:
        name: Logger name (usually __name__)
        agent_id: Optional agent identifier
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Set logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = A2ALogFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Set agent ID if provided
    if agent_id:
        logger.agent_id = agent_id
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def setup_system_logging(level: str = "INFO"):
    """
    Setup system-wide logging configuration
    
    Args:
        level: Logging level for the entire system
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = A2ALogFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels for external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


class A2ALogger:
    """
    Enhanced logger class for A2A agents with structured logging
    """
    
    def __init__(self, agent_id: str, agent_type: str = "agent"):
        """
        Initialize A2A logger
        
        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (coordinator, remote, internal)
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.logger = get_logger(f"a2a.{agent_type}.{agent_id}", agent_id)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with additional context"""
        self.logger.debug(f"{message}", extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with additional context"""
        self.logger.info(f"{message}", extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with additional context"""
        self.logger.warning(f"{message}", extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with additional context"""
        self.logger.error(f"{message}", extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with additional context"""
        self.logger.critical(f"{message}", extra=kwargs)
    
    def log_task_start(self, task_id: str, task_type: str):
        """Log task start"""
        self.info(f"Task started: {task_id} (type: {task_type})", 
                 task_id=task_id, task_type=task_type)
    
    def log_task_complete(self, task_id: str, duration: float):
        """Log task completion"""
        self.info(f"Task completed: {task_id} (duration: {duration:.2f}s)", 
                 task_id=task_id, duration=duration)
    
    def log_task_error(self, task_id: str, error: str):
        """Log task error"""
        self.error(f"Task failed: {task_id} - {error}", 
                  task_id=task_id, error=error)
    
    def log_protocol_message(self, message_type: str, target: str, direction: str):
        """Log A2A protocol message"""
        self.debug(f"Protocol message: {direction} {message_type} to {target}", 
                  message_type=message_type, target=target, direction=direction)
    
    def log_agent_communication(self, target_agent: str, operation: str, success: bool):
        """Log agent communication"""
        status = "success" if success else "failed"
        self.info(f"Agent communication: {operation} with {target_agent} - {status}", 
                 target_agent=target_agent, operation=operation, success=success)
