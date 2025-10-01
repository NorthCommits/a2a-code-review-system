"""
Discovery Service

This module implements the agent discovery service for the A2A system.
Provides APIs for discovering agents based on task requirements.
"""

import asyncio
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from .agent_registry import AgentRegistry
from .capability_matcher import CapabilityMatcher
from a2a_protocol.message_schema import AgentInfo
from utils.logger import get_logger

logger = get_logger(__name__)


class DiscoveryService:
    """
    Agent discovery service for the A2A system
    
    Provides REST API endpoints for discovering agents based on
    capabilities and task requirements.
    """
    
    def __init__(self, registry: AgentRegistry, port: int = 8080):
        """
        Initialize discovery service
        
        Args:
            registry: Agent registry instance
            port: Port for the discovery service
        """
        self.registry = registry
        self.port = port
        self.app = FastAPI(
            title="A2A Discovery Service",
            description="Agent discovery and capability matching service",
            version="1.0.0"
        )
        
        # Register API endpoints
        self._register_endpoints()
    
    def _register_endpoints(self):
        """Register FastAPI endpoints"""
        
        @self.app.get("/agents", response_model=List[Dict[str, Any]])
        async def get_all_agents():
            """Get all registered agents"""
            try:
                agents = self.registry.get_all_agents()
                return [agent.dict() for agent in agents]
            except Exception as e:
                logger.error(f"Error getting all agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agents/{agent_id}", response_model=Dict[str, Any])
        async def get_agent(agent_id: str):
            """Get specific agent by ID"""
            try:
                agent = self.registry.get_agent(agent_id)
                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")
                return agent.dict()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agents/active", response_model=List[Dict[str, Any]])
        async def get_active_agents():
            """Get all active agents"""
            try:
                agents = self.registry.get_active_agents()
                return [agent.dict() for agent in agents]
            except Exception as e:
                logger.error(f"Error getting active agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/capabilities", response_model=List[str])
        async def get_all_capabilities():
            """Get all available capabilities"""
            try:
                capabilities = list(self.registry.capability_matcher.all_capabilities)
                return sorted(capabilities)
            except Exception as e:
                logger.error(f"Error getting capabilities: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/capabilities/{capability_name}/agents", response_model=List[Dict[str, Any]])
        async def get_agents_by_capability(capability_name: str):
            """Get agents that have a specific capability"""
            try:
                agents = self.registry.find_agents_by_capability(capability_name)
                return [agent.dict() for agent in agents]
            except Exception as e:
                logger.error(f"Error getting agents by capability {capability_name}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/discover", response_model=Dict[str, Any])
        async def discover_agents(
            capabilities: List[str] = Query(..., description="Required capabilities"),
            max_agents: int = Query(10, description="Maximum number of agents to return")
        ):
            """Discover agents based on required capabilities"""
            try:
                if not capabilities:
                    raise HTTPException(status_code=400, detail="At least one capability is required")
                
                # Find agents with all required capabilities
                matching_agents = self.registry.find_agents_by_capabilities(capabilities)
                
                # Limit results
                if len(matching_agents) > max_agents:
                    matching_agents = matching_agents[:max_agents]
                
                # Calculate capability coverage
                coverage = self.registry.capability_matcher.get_capability_coverage(capabilities)
                
                return {
                    "required_capabilities": capabilities,
                    "matching_agents": [agent.dict() for agent in matching_agents],
                    "total_matches": len(matching_agents),
                    "capability_coverage": coverage,
                    "suggestions": self.registry.capability_matcher.suggest_capability_improvements(capabilities)
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error discovering agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/discover/best", response_model=Dict[str, Any])
        async def discover_best_agent(
            capabilities: List[str] = Query(..., description="Required capabilities")
        ):
            """Discover the best agent for given capabilities"""
            try:
                if not capabilities:
                    raise HTTPException(status_code=400, detail="At least one capability is required")
                
                best_agent = self.registry.find_best_agent(capabilities)
                
                if not best_agent:
                    return {
                        "agent": None,
                        "message": "No suitable agent found",
                        "suggestions": self.registry.capability_matcher.suggest_capability_improvements(capabilities)
                    }
                
                # Calculate score for transparency
                score = self.registry.capability_matcher._calculate_agent_score(best_agent, capabilities)
                
                return {
                    "agent": best_agent.dict(),
                    "score": score,
                    "reason": "Best match based on capability coverage and agent status"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error discovering best agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health", response_model=Dict[str, Any])
        async def health_check():
            """Health check endpoint"""
            try:
                summary = self.registry.get_registry_summary()
                return {
                    "status": "healthy",
                    "registry": summary,
                    "service": "A2A Discovery Service"
                }
            except Exception as e:
                logger.error(f"Health check error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/statistics", response_model=Dict[str, Any])
        async def get_statistics():
            """Get discovery service statistics"""
            try:
                agent_stats = self.registry.get_agent_statistics()
                capability_stats = self.registry.capability_matcher.get_capability_statistics()
                registry_summary = self.registry.get_registry_summary()
                
                return {
                    "registry": registry_summary,
                    "agents": agent_stats,
                    "capabilities": capability_stats
                }
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/agents/{agent_id}/status")
        async def update_agent_status(
            agent_id: str,
            status: str = Query(..., description="New status (active, inactive, maintenance)")
        ):
            """Update agent status"""
            try:
                if status not in ["active", "inactive", "maintenance"]:
                    raise HTTPException(status_code=400, detail="Invalid status")
                
                self.registry.update_agent_status(agent_id, status)
                return {"message": f"Agent {agent_id} status updated to {status}"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error updating agent status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def start(self):
        """Start the discovery service"""
        import uvicorn
        
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Starting A2A Discovery Service on port {self.port}")
        await server.serve()
    
    def get_service_url(self) -> str:
        """Get the discovery service URL"""
        return f"http://localhost:{self.port}"
