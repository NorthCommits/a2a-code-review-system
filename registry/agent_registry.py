"""
Agent Registry

This module implements the central agent registry for the A2A system.
Manages agent registration, health monitoring, and capability tracking.
"""

import json
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import httpx
from .capability_matcher import CapabilityMatcher
from a2a_protocol.message_schema import AgentInfo, AgentCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentRegistryError(Exception):
    """Custom exception for agent registry errors"""
    pass


class AgentRegistry:
    """
    Central registry for managing A2A agents
    
    Handles agent registration, discovery, health monitoring,
    and capability matching for the A2A protocol system.
    """
    
    def __init__(self, config_file: str = "registry_config.json"):
        """
        Initialize agent registry
        
        Args:
            config_file: Path to registry configuration file
        """
        self.config_file = config_file
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_status: Dict[str, Dict[str, any]] = {}
        self.capability_matcher = CapabilityMatcher()
        self.health_check_client = httpx.AsyncClient(timeout=5.0)
        self.health_check_task = None
        
        # Load initial configuration
        self._load_config()
    
    def _load_config(self):
        """Load agent configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Register agents from config
            for agent_config in config.get("agents", []):
                agent_info = AgentInfo(**agent_config)
                self.register_agent(agent_info)
            
            # Store registry configuration
            self.registry_config = config.get("registry_config", {})
            
            logger.info(f"Loaded {len(self.agents)} agents from configuration")
            
        except Exception as e:
            logger.error(f"Error loading registry config: {e}")
            raise AgentRegistryError(f"Failed to load config: {e}")
    
    def register_agent(self, agent_info: AgentInfo) -> bool:
        """
        Register a new agent in the registry
        
        Args:
            agent_info: Agent information
            
        Returns:
            True if registration was successful
        """
        try:
            agent_id = agent_info.agent_id
            
            # Check if agent already exists
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already registered, updating")
            
            # Register agent
            self.agents[agent_id] = agent_info
            
            # Initialize status tracking
            self.agent_status[agent_id] = {
                "status": agent_info.status,
                "last_health_check": None,
                "health_status": "unknown",
                "active_tasks": 0,
                "total_tasks": 0,
                "last_seen": datetime.utcnow(),
                "response_time": None
            }
            
            # Update capability matcher
            self.capability_matcher.add_agent(agent_info)
            
            logger.info(f"Registered agent: {agent_id} ({agent_info.name})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_info.agent_id}: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if unregistration was successful
        """
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found in registry")
                return False
            
            # Remove from registry
            agent_info = self.agents.pop(agent_id)
            self.agent_status.pop(agent_id, None)
            
            # Update capability matcher
            self.capability_matcher.remove_agent(agent_id)
            
            logger.info(f"Unregistered agent: {agent_id} ({agent_info.name})")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get agent information by ID
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information or None if not found
        """
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[AgentInfo]:
        """Get all registered agents"""
        return list(self.agents.values())
    
    def get_active_agents(self) -> List[AgentInfo]:
        """Get all active agents"""
        return [
            agent for agent in self.agents.values()
            if self.agent_status.get(agent.agent_id, {}).get("status") == "active"
        ]
    
    def find_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """
        Find agents that have a specific capability
        
        Args:
            capability_name: Name of the capability
            
        Returns:
            List of agents with the capability
        """
        return self.capability_matcher.find_agents_by_capability(capability_name)
    
    def find_best_agent(self, required_capabilities: List[str]) -> Optional[AgentInfo]:
        """
        Find the best agent for given capabilities
        
        Args:
            required_capabilities: List of required capability names
            
        Returns:
            Best matching agent or None
        """
        return self.capability_matcher.find_best_agent(required_capabilities)
    
    async def check_agent_health(self, agent_id: str) -> bool:
        """
        Check health of a specific agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent is healthy
        """
        agent_info = self.get_agent(agent_id)
        if not agent_info or not agent_info.health_check_endpoint:
            return False
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.health_check_client.get(
                agent_info.health_check_endpoint,
                timeout=5.0
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            is_healthy = response.status_code == 200
            
            # Update agent status
            if agent_id in self.agent_status:
                self.agent_status[agent_id].update({
                    "last_health_check": datetime.utcnow(),
                    "health_status": "healthy" if is_healthy else "unhealthy",
                    "response_time": response_time,
                    "last_seen": datetime.utcnow()
                })
            
            logger.debug(f"Health check for {agent_id}: {'healthy' if is_healthy else 'unhealthy'}")
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed for {agent_id}: {e}")
            
            # Update status as unhealthy
            if agent_id in self.agent_status:
                self.agent_status[agent_id].update({
                    "last_health_check": datetime.utcnow(),
                    "health_status": "unhealthy",
                    "response_time": None
                })
            
            return False
    
    async def check_all_agents_health(self):
        """Check health of all registered agents"""
        if not self.agents:
            return
        
        tasks = [
            self.check_agent_health(agent_id)
            for agent_id in self.agents.keys()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Completed health check for all agents")
    
    def start_health_monitoring(self, interval_seconds: int = 30):
        """
        Start periodic health monitoring
        
        Args:
            interval_seconds: Health check interval in seconds
        """
        async def health_monitor():
            while True:
                try:
                    await self.check_all_agents_health()
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(interval_seconds)
        
        self.health_check_task = asyncio.create_task(health_monitor())
        logger.info(f"Started health monitoring with {interval_seconds}s interval")
    
    def stop_health_monitoring(self):
        """Stop periodic health monitoring"""
        if self.health_check_task:
            self.health_check_task.cancel()
            self.health_check_task = None
            logger.info("Stopped health monitoring")
    
    def update_agent_status(self, agent_id: str, status: str):
        """
        Update agent status
        
        Args:
            agent_id: Agent identifier
            status: New status (active, inactive, maintenance)
        """
        if agent_id in self.agent_status:
            self.agent_status[agent_id]["status"] = status
            logger.info(f"Updated agent {agent_id} status to {status}")
    
    def increment_task_count(self, agent_id: str):
        """Increment active task count for agent"""
        if agent_id in self.agent_status:
            self.agent_status[agent_id]["active_tasks"] += 1
            self.agent_status[agent_id]["total_tasks"] += 1
    
    def decrement_task_count(self, agent_id: str):
        """Decrement active task count for agent"""
        if agent_id in self.agent_status:
            self.agent_status[agent_id]["active_tasks"] = max(
                0, self.agent_status[agent_id]["active_tasks"] - 1
            )
    
    def get_agent_statistics(self) -> Dict[str, Dict[str, any]]:
        """Get statistics for all agents"""
        return {
            agent_id: {
                "name": agent.name,
                "status": status_info["status"],
                "health_status": status_info["health_status"],
                "active_tasks": status_info["active_tasks"],
                "total_tasks": status_info["total_tasks"],
                "response_time": status_info["response_time"],
                "last_seen": status_info["last_seen"].isoformat() if status_info["last_seen"] else None
            }
            for agent_id, agent in self.agents.items()
            for status_info in [self.agent_status.get(agent_id, {})]
        }
    
    def get_registry_summary(self) -> Dict[str, any]:
        """Get registry summary information"""
        total_agents = len(self.agents)
        active_agents = len([a for a in self.agent_status.values() if a["status"] == "active"])
        healthy_agents = len([a for a in self.agent_status.values() if a["health_status"] == "healthy"])
        
        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "healthy_agents": healthy_agents,
            "total_capabilities": len(self.capability_matcher.all_capabilities),
            "registry_uptime": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """Close registry and cleanup resources"""
        self.stop_health_monitoring()
        await self.health_check_client.aclose()
        logger.info("Agent registry closed")
