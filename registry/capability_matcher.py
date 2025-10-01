"""
Capability Matcher

This module implements capability matching logic for the A2A agent registry.
Matches tasks to appropriate agents based on their capabilities.
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict
from a2a_protocol.message_schema import AgentInfo, AgentCapability
from utils.logger import get_logger

logger = get_logger(__name__)


class CapabilityMatchError(Exception):
    """Custom exception for capability matching errors"""
    pass


class CapabilityMatcher:
    """
    Matches tasks to agents based on their capabilities
    
    Provides intelligent matching of analysis tasks to the most
    appropriate agents based on capability requirements and agent status.
    """
    
    def __init__(self):
        """Initialize capability matcher"""
        self.agents: Dict[str, AgentInfo] = {}
        self.capability_index: Dict[str, Set[str]] = defaultdict(set)
        self.all_capabilities: Set[str] = set()
    
    def add_agent(self, agent_info: AgentInfo):
        """
        Add agent to capability matcher
        
        Args:
            agent_info: Agent information
        """
        agent_id = agent_info.agent_id
        self.agents[agent_id] = agent_info
        
        # Index capabilities
        for capability in agent_info.capabilities:
            capability_name = capability.name
            self.capability_index[capability_name].add(agent_id)
            self.all_capabilities.add(capability_name)
        
        logger.debug(f"Added agent {agent_id} with capabilities: {[c.name for c in agent_info.capabilities]}")
    
    def remove_agent(self, agent_id: str):
        """
        Remove agent from capability matcher
        
        Args:
            agent_id: Agent identifier
        """
        if agent_id not in self.agents:
            return
        
        agent_info = self.agents[agent_id]
        
        # Remove from capability index
        for capability in agent_info.capabilities:
            capability_name = capability.name
            self.capability_index[capability_name].discard(agent_id)
            
            # Remove capability if no agents have it
            if not self.capability_index[capability_name]:
                del self.capability_index[capability_name]
                self.all_capabilities.discard(capability_name)
        
        del self.agents[agent_id]
        logger.debug(f"Removed agent {agent_id}")
    
    def find_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """
        Find agents that have a specific capability
        
        Args:
            capability_name: Name of the capability
            
        Returns:
            List of agents with the capability
        """
        agent_ids = self.capability_index.get(capability_name, set())
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    def find_agents_by_capabilities(self, capability_names: List[str]) -> List[AgentInfo]:
        """
        Find agents that have all specified capabilities
        
        Args:
            capability_names: List of capability names
            
        Returns:
            List of agents that have all capabilities
        """
        if not capability_names:
            return []
        
        # Start with agents that have the first capability
        agent_ids = self.capability_index.get(capability_names[0], set()).copy()
        
        # Intersect with agents that have each subsequent capability
        for capability_name in capability_names[1:]:
            agent_ids &= self.capability_index.get(capability_name, set())
        
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    def find_best_agent(self, required_capabilities: List[str]) -> Optional[AgentInfo]:
        """
        Find the best agent for given capabilities
        
        Args:
            required_capabilities: List of required capability names
            
        Returns:
            Best matching agent or None
        """
        if not required_capabilities:
            return None
        
        # Find agents with all required capabilities
        candidate_agents = self.find_agents_by_capabilities(required_capabilities)
        
        if not candidate_agents:
            logger.warning(f"No agents found with all required capabilities: {required_capabilities}")
            return None
        
        # Score agents based on multiple factors
        best_agent = None
        best_score = -1
        
        for agent in candidate_agents:
            score = self._calculate_agent_score(agent, required_capabilities)
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        logger.info(f"Selected best agent {best_agent.agent_id} with score {best_score}")
        return best_agent
    
    def _calculate_agent_score(self, agent: AgentInfo, required_capabilities: List[str]) -> float:
        """
        Calculate score for agent based on capabilities and other factors
        
        Args:
            agent: Agent information
            required_capabilities: Required capabilities
            
        Returns:
            Agent score (higher is better)
        """
        score = 0.0
        
        # Base score for having required capabilities
        agent_capability_names = {cap.name for cap in agent.capabilities}
        matching_capabilities = len(set(required_capabilities) & agent_capability_names)
        score += matching_capabilities * 10.0
        
        # Bonus for having additional relevant capabilities
        additional_capabilities = len(agent_capability_names - set(required_capabilities))
        score += additional_capabilities * 2.0
        
        # Priority bonus (from registry config)
        if hasattr(agent, 'priority') and agent.priority:
            score += (10 - agent.priority) * 0.5  # Lower priority number = higher score
        
        # Status bonus
        if agent.status == "active":
            score += 5.0
        elif agent.status == "maintenance":
            score += 1.0
        
        # Capability quality bonus (more detailed capabilities)
        for capability in agent.capabilities:
            if capability.parameters:
                score += len(capability.parameters) * 0.1
        
        return score
    
    def get_capability_coverage(self, capability_names: List[str]) -> Dict[str, float]:
        """
        Get coverage statistics for capabilities
        
        Args:
            capability_names: List of capability names to analyze
            
        Returns:
            Coverage statistics
        """
        coverage = {}
        total_agents = len(self.agents)
        
        if total_agents == 0:
            return {cap: 0.0 for cap in capability_names}
        
        for capability_name in capability_names:
            agents_with_capability = len(self.capability_index.get(capability_name, set()))
            coverage[capability_name] = agents_with_capability / total_agents
        
        return coverage
    
    def suggest_capability_improvements(self, required_capabilities: List[str]) -> List[str]:
        """
        Suggest capability improvements based on gaps
        
        Args:
            required_capabilities: Required capabilities
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Check for missing capabilities
        missing_capabilities = set(required_capabilities) - self.all_capabilities
        if missing_capabilities:
            suggestions.append(f"Missing capabilities: {', '.join(missing_capabilities)}")
        
        # Check for low coverage capabilities
        coverage = self.get_capability_coverage(required_capabilities)
        low_coverage = [cap for cap, cov in coverage.items() if cov < 0.5]
        if low_coverage:
            suggestions.append(f"Low coverage capabilities: {', '.join(low_coverage)}")
        
        # Check for agents with too many responsibilities
        agent_capability_counts = {
            agent_id: len(agent.capabilities)
            for agent_id, agent in self.agents.items()
        }
        
        if agent_capability_counts:
            max_capabilities = max(agent_capability_counts.values())
            overloaded_agents = [
                agent_id for agent_id, count in agent_capability_counts.items()
                if count > max_capabilities * 0.8
            ]
            
            if overloaded_agents:
                suggestions.append(f"Overloaded agents: {', '.join(overloaded_agents)}")
        
        return suggestions
    
    def get_capability_statistics(self) -> Dict[str, any]:
        """Get capability matching statistics"""
        total_agents = len(self.agents)
        total_capabilities = len(self.all_capabilities)
        
        # Calculate capability distribution
        capability_counts = {
            capability: len(agent_ids)
            for capability, agent_ids in self.capability_index.items()
        }
        
        # Calculate agent capability distribution
        agent_capability_counts = [
            len(agent.capabilities)
            for agent in self.agents.values()
        ]
        
        return {
            "total_agents": total_agents,
            "total_capabilities": total_capabilities,
            "capability_distribution": capability_counts,
            "avg_capabilities_per_agent": sum(agent_capability_counts) / len(agent_capability_counts) if agent_capability_counts else 0,
            "max_capabilities_per_agent": max(agent_capability_counts) if agent_capability_counts else 0,
            "min_capabilities_per_agent": min(agent_capability_counts) if agent_capability_counts else 0
        }
