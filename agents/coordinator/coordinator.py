"""
Coordinator Agent

This module implements the main coordinator agent that orchestrates
code analysis across multiple specialized remote agents.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from agents.base.client_agent import ClientAgent
from .task_distributor import TaskDistributor
from .result_aggregator import ResultAggregator
from .orchestration_engine import OrchestrationEngine
from a2a_protocol.message_schema import AnalysisResult, TaskStatus
from registry.agent_registry import AgentRegistry
from utils.logger import A2ALogger


class CoordinatorAgent(ClientAgent):
    """
    Main coordinator agent for the A2A code review system
    
    Orchestrates code analysis by distributing tasks to specialized
    remote agents and aggregating their results.
    """
    
    def __init__(
        self, 
        registry: AgentRegistry,
        timeout: int = 60
    ):
        """
        Initialize coordinator agent
        
        Args:
            registry: Agent registry for discovery
            timeout: Request timeout in seconds
        """
        super().__init__("coordinator-001", "Code Review Coordinator", registry, timeout)
        
        # Initialize components
        self.task_distributor = TaskDistributor(registry)
        self.result_aggregator = ResultAggregator()
        self.orchestration_engine = OrchestrationEngine()
        
        self.logger = A2ALogger("coordinator-001", "coordinator")
        
        # Analysis configuration
        self.analysis_config = {
            "syntax_check": {
                "capabilities": ["syntax_check", "linting", "style_validation"],
                "priority": 1
            },
            "security_scan": {
                "capabilities": ["vulnerability_scan", "sql_injection_check", "xss_detection"],
                "priority": 2
            },
            "performance_analysis": {
                "capabilities": ["complexity_analysis", "optimization_suggestions", "memory_analysis"],
                "priority": 3
            },
            "documentation_check": {
                "capabilities": ["docstring_validation", "comment_analysis", "readability_assessment"],
                "priority": 4
            },
            "test_coverage": {
                "capabilities": ["coverage_analysis", "test_quality_assessment", "missing_test_suggestions"],
                "priority": 5
            }
        }
        
        self.logger.info("Initialized Code Review Coordinator")
    
    async def analyze_code(self, code: str, language: str = "python", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze code using all available specialized agents
        
        Args:
            code: Code to analyze
            language: Programming language
            options: Optional analysis options
            
        Returns:
            Comprehensive analysis results
        """
        try:
            analysis_id = f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"Starting comprehensive code analysis: {analysis_id}")
            
            # Prepare task parameters
            task_params = {
                "code": code,
                "language": language,
                "options": options or {},
                "analysis_id": analysis_id
            }
            
            # Distribute tasks to specialized agents
            distributed_tasks = await self.task_distributor.distribute_analysis_tasks(
                task_params, 
                self.analysis_config
            )
            
            if not distributed_tasks:
                raise Exception("No agents available for analysis")
            
            self.logger.info(f"Distributed {len(distributed_tasks)} analysis tasks")
            
            # Wait for all tasks to complete
            results = await self.wait_for_completion(
                list(distributed_tasks.values()),
                timeout=self.timeout
            )
            
            # Aggregate results from all agents
            aggregated_result = self.result_aggregator.aggregate_results(results)
            
            # Apply orchestration rules
            final_result = self.orchestration_engine.apply_orchestration_rules(
                aggregated_result, 
                analysis_id
            )
            
            self.logger.info(f"Completed comprehensive analysis: {analysis_id}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive code analysis: {e}")
            return {
                "analysis_id": analysis_id if 'analysis_id' in locals() else None,
                "status": "failed",
                "error": str(e),
                "results": {},
                "summary": {
                    "total_observations": 0,
                    "total_errors": 1,
                    "total_suggestions": 0,
                    "corrected_code": code
                }
            }
    
    async def analyze_specific_aspect(
        self, 
        code: str, 
        aspect: str, 
        language: str = "python"
    ) -> Optional[AnalysisResult]:
        """
        Analyze a specific aspect of the code
        
        Args:
            code: Code to analyze
            aspect: Analysis aspect (syntax_check, security_scan, etc.)
            language: Programming language
            
        Returns:
            Analysis result for the specific aspect
        """
        try:
            if aspect not in self.analysis_config:
                raise ValueError(f"Unknown analysis aspect: {aspect}")
            
            config = self.analysis_config[aspect]
            
            # Find best agent for this aspect
            task_id = await self.send_task_by_capability(
                config["capabilities"],
                {
                    "code": code,
                    "language": language,
                    "analysis_type": aspect
                },
                "analyze_code"
            )
            
            if not task_id:
                raise Exception(f"No agent available for {aspect}")
            
            # Wait for result
            result = await self.get_task_result(task_id)
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing {aspect}: {e}")
            return None
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all available agents
        
        Returns:
            Agent status information
        """
        try:
            if not self.registry:
                return {"error": "No registry available"}
            
            agent_stats = self.registry.get_agent_statistics()
            registry_summary = self.registry.get_registry_summary()
            
            return {
                "registry": registry_summary,
                "agents": agent_stats,
                "coordinator_status": self.get_status()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return {"error": str(e)}
    
    async def register_with_registry(self) -> bool:
        """
        Register coordinator with the agent registry
        
        Returns:
            True if registration was successful
        """
        try:
            # Coordinator doesn't need to register itself as it's not a remote agent
            # But we can validate that the registry is working
            if not self.registry:
                return False
            
            # Test registry connectivity
            summary = self.registry.get_registry_summary()
            self.logger.info(f"Registry connectivity confirmed: {summary}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to registry: {e}")
            return False
    
    def get_analysis_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available analysis capabilities
        
        Returns:
            Dictionary of analysis capabilities and their configurations
        """
        return self.analysis_config.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Health status information
        """
        try:
            coordinator_health = super().health_check()
            
            # Check registry health
            registry_health = {"status": "unknown"}
            if self.registry:
                try:
                    registry_summary = self.registry.get_registry_summary()
                    registry_health = {
                        "status": "healthy",
                        "active_agents": registry_summary["active_agents"],
                        "healthy_agents": registry_summary["healthy_agents"]
                    }
                except Exception as e:
                    registry_health = {"status": "unhealthy", "error": str(e)}
            
            # Check pending tasks
            pending_tasks = len(self.get_pending_tasks())
            
            overall_status = "healthy"
            if registry_health["status"] != "healthy" or pending_tasks > 10:
                overall_status = "degraded"
            
            return {
                "status": overall_status,
                "coordinator": coordinator_health,
                "registry": registry_health,
                "pending_tasks": pending_tasks,
                "analysis_capabilities": len(self.analysis_capabilities)
            }
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
