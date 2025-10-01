"""
Task Distributor

This module implements task distribution logic for the coordinator agent.
Distributes analysis tasks to appropriate remote agents based on capabilities.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from registry.agent_registry import AgentRegistry
from a2a_protocol.message_schema import AgentInfo
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskDistributor:
    """
    Distributes analysis tasks to appropriate remote agents
    
    Handles the logic for matching tasks to agents based on
    capabilities and current agent status.
    """
    
    def __init__(self, registry: AgentRegistry):
        """
        Initialize task distributor
        
        Args:
            registry: Agent registry for agent discovery
        """
        self.registry = registry
        self.logger = get_logger(__name__)
        
        # Task distribution strategy
        self.distribution_strategy = "capability_based"  # or "round_robin", "load_balanced"
        
        self.logger.info("Initialized Task Distributor")
    
    async def distribute_analysis_tasks(
        self, 
        task_params: Dict[str, Any], 
        analysis_config: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Distribute analysis tasks to appropriate agents
        
        Args:
            task_params: Task parameters
            analysis_config: Analysis configuration mapping
            
        Returns:
            Dictionary mapping analysis types to task IDs
        """
        distributed_tasks = {}
        
        try:
            for analysis_type, config in analysis_config.items():
                task_id = await self._distribute_single_task(
                    analysis_type,
                    task_params,
                    config
                )
                
                if task_id:
                    distributed_tasks[analysis_type] = task_id
                    self.logger.info(f"Distributed {analysis_type} task: {task_id}")
                else:
                    self.logger.warning(f"Failed to distribute {analysis_type} task")
            
            return distributed_tasks
            
        except Exception as e:
            self.logger.error(f"Error distributing analysis tasks: {e}")
            return distributed_tasks
    
    async def _distribute_single_task(
        self, 
        analysis_type: str, 
        task_params: Dict[str, Any], 
        config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Distribute a single analysis task
        
        Args:
            analysis_type: Type of analysis
            task_params: Task parameters
            config: Analysis configuration
            
        Returns:
            Task ID if successful, None otherwise
        """
        try:
            required_capabilities = config.get("capabilities", [])
            priority = config.get("priority", 1)
            
            # Find best agent for this analysis type
            best_agent = self.registry.find_best_agent(required_capabilities)
            
            if not best_agent:
                self.logger.warning(f"No agent found for {analysis_type} with capabilities: {required_capabilities}")
                return None
            
            # Check agent health
            is_healthy = await self.registry.check_agent_health(best_agent.agent_id)
            if not is_healthy:
                self.logger.warning(f"Agent {best_agent.agent_id} is unhealthy, skipping {analysis_type}")
                return None
            
            # Check agent capacity
            agent_stats = self.registry.agent_status.get(best_agent.agent_id, {})
            active_tasks = agent_stats.get("active_tasks", 0)
            max_concurrent = getattr(best_agent, 'max_concurrent_tasks', 5)
            
            if active_tasks >= max_concurrent:
                self.logger.warning(f"Agent {best_agent.agent_id} at capacity ({active_tasks}/{max_concurrent})")
                return None
            
            # Create enhanced task parameters
            enhanced_params = {
                **task_params,
                "analysis_type": analysis_type,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # This would normally send the task via A2A protocol
            # For now, we'll return a mock task ID
            task_id = f"{analysis_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Update agent task count
            self.registry.increment_task_count(best_agent.agent_id)
            
            self.logger.info(f"Successfully distributed {analysis_type} to agent {best_agent.agent_id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Error distributing {analysis_type} task: {e}")
            return None
    
    def get_distribution_strategy(self) -> str:
        """Get current distribution strategy"""
        return self.distribution_strategy
    
    def set_distribution_strategy(self, strategy: str):
        """
        Set distribution strategy
        
        Args:
            strategy: Distribution strategy (capability_based, round_robin, load_balanced)
        """
        valid_strategies = ["capability_based", "round_robin", "load_balanced"]
        if strategy in valid_strategies:
            self.distribution_strategy = strategy
            self.logger.info(f"Distribution strategy changed to: {strategy}")
        else:
            self.logger.warning(f"Invalid distribution strategy: {strategy}")
    
    def get_agent_load_balance_info(self) -> Dict[str, Any]:
        """
        Get agent load balancing information
        
        Returns:
            Load balancing statistics
        """
        try:
            agent_stats = self.registry.get_agent_statistics()
            
            load_info = {}
            for agent_id, stats in agent_stats.items():
                load_info[agent_id] = {
                    "name": stats["name"],
                    "active_tasks": stats["active_tasks"],
                    "total_tasks": stats["total_tasks"],
                    "health_status": stats["health_status"],
                    "response_time": stats["response_time"]
                }
            
            return {
                "distribution_strategy": self.distribution_strategy,
                "agents": load_info,
                "total_active_tasks": sum(stats["active_tasks"] for stats in agent_stats.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error getting load balance info: {e}")
            return {"error": str(e)}
    
    def suggest_agent_optimization(self) -> List[str]:
        """
        Suggest agent optimization based on current load
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        try:
            load_info = self.get_agent_load_balance_info()
            agents = load_info.get("agents", {})
            
            # Check for overloaded agents
            overloaded_agents = [
                agent_id for agent_id, info in agents.items()
                if info["active_tasks"] > 5  # Threshold for overloaded
            ]
            
            if overloaded_agents:
                suggestions.append(f"Consider load balancing for overloaded agents: {', '.join(overloaded_agents)}")
            
            # Check for underutilized agents
            underutilized_agents = [
                agent_id for agent_id, info in agents.items()
                if info["active_tasks"] == 0 and info["health_status"] == "healthy"
            ]
            
            if underutilized_agents:
                suggestions.append(f"Underutilized healthy agents available: {', '.join(underutilized_agents)}")
            
            # Check for unhealthy agents
            unhealthy_agents = [
                agent_id for agent_id, info in agents.items()
                if info["health_status"] == "unhealthy"
            ]
            
            if unhealthy_agents:
                suggestions.append(f"Unhealthy agents need attention: {', '.join(unhealthy_agents)}")
            
            # Suggest strategy changes
            if self.distribution_strategy == "capability_based":
                if len(overloaded_agents) > len(agents) / 2:
                    suggestions.append("Consider switching to load_balanced strategy")
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {e}")
            suggestions.append(f"Error generating suggestions: {e}")
        
        return suggestions
