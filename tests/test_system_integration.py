"""
System Integration Tests

This module contains integration tests for the A2A Code Review System.
Tests the complete workflow from code input to analysis results.
"""

import pytest
import asyncio
import json
from typing import Dict, Any

from registry.agent_registry import AgentRegistry
from agents.coordinator.coordinator import CoordinatorAgent
from agents.remote.syntax_agent import SyntaxAgent
from analyzers.syntax_analyzer import SyntaxAnalyzer


class TestSystemIntegration:
    """Test system integration and end-to-end workflows"""
    
    @pytest.fixture
    async def registry(self):
        """Create test registry"""
        registry = AgentRegistry("registry/registry_config.json")
        return registry
    
    @pytest.fixture
    async def coordinator(self, registry):
        """Create test coordinator"""
        coordinator = CoordinatorAgent(registry)
        await coordinator.start()
        return coordinator
    
    @pytest.fixture
    def sample_code(self):
        """Sample code for testing"""
        return '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def process_user_input(user_input):
    # Potential SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return query

def inefficient_sort(data):
    # Inefficient bubble sort implementation
    for i in range(len(data)):
        for j in range(len(data) - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
'''
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization"""
        assert registry is not None
        assert len(registry.agents) > 0
        
        # Check that agents are loaded from config
        agent_ids = list(registry.agents.keys())
        assert "syntax-analyzer-001" in agent_ids
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """Test coordinator initialization"""
        assert coordinator is not None
        assert coordinator.agent_id == "coordinator-001"
        assert coordinator.status == "active"
    
    @pytest.mark.asyncio
    async def test_syntax_analyzer(self, sample_code):
        """Test syntax analyzer functionality"""
        analyzer = SyntaxAnalyzer()
        
        result = await analyzer.analyze_code(sample_code, "python")
        
        assert result is not None
        assert "observations" in result
        assert "errors" in result
        assert "suggestions" in result
        assert "quality_score" in result
        
        # Should find some observations about the inefficient code
        assert len(result["observations"]) > 0
    
    @pytest.mark.asyncio
    async def test_syntax_agent(self, sample_code):
        """Test syntax agent functionality"""
        agent = SyntaxAgent(port=5001)
        
        # Test task parameters
        task_params = {
            "code": sample_code,
            "language": "python",
            "task_id": "test_task_001",
            "options": {}
        }
        
        result = await agent.analyze_code(task_params)
        
        assert result is not None
        assert result.status == "completed"
        assert len(result.observations) > 0
        assert result.agent_id == "syntax-analyzer-001"
    
    @pytest.mark.asyncio
    async def test_agent_registry_discovery(self, registry):
        """Test agent discovery functionality"""
        # Test finding agents by capability
        syntax_agents = registry.find_agents_by_capability("syntax_check")
        assert len(syntax_agents) > 0
        
        # Test finding best agent
        best_agent = registry.find_best_agent(["syntax_check", "linting"])
        assert best_agent is not None
        assert best_agent.agent_id == "syntax-analyzer-001"
    
    @pytest.mark.asyncio
    async def test_task_distribution(self, coordinator, sample_code):
        """Test task distribution functionality"""
        # Test distributing tasks to agents
        task_params = {
            "code": sample_code,
            "language": "python",
            "options": {}
        }
        
        # This would normally distribute to real agents
        # For testing, we'll just verify the coordinator can handle the request
        assert coordinator.task_distributor is not None
        assert coordinator.result_aggregator is not None
        assert coordinator.orchestration_engine is not None
    
    @pytest.mark.asyncio
    async def test_result_aggregation(self, coordinator):
        """Test result aggregation functionality"""
        # Mock analysis results
        mock_results = {
            "syntax-analyzer-001": {
                "agent_id": "syntax-analyzer-001",
                "task_id": "test_task_001",
                "status": "completed",
                "observations": [
                    {
                        "type": "function_length",
                        "message": "Function is too long",
                        "severity": "warning",
                        "line_number": 1
                    }
                ],
                "errors": [
                    {
                        "type": "line_length",
                        "message": "Line too long",
                        "severity": "warning",
                        "line_number": 5
                    }
                ],
                "suggestions": [
                    {
                        "type": "documentation",
                        "message": "Add docstrings",
                        "priority": "medium"
                    }
                ],
                "corrected_code": None,
                "metadata": {}
            }
        }
        
        # Test aggregation
        aggregated = coordinator.result_aggregator.aggregate_results(mock_results)
        
        assert aggregated is not None
        assert "observations" in aggregated
        assert "errors" in aggregated
        assert "suggestions" in aggregated
        assert "summary" in aggregated
        assert aggregated["total_agents"] == 1
        assert aggregated["successful_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_orchestration_rules(self, coordinator):
        """Test orchestration rules application"""
        # Mock aggregated result
        mock_result = {
            "total_agents": 1,
            "successful_agents": 1,
            "observations": [],
            "errors": [
                {
                    "type": "syntax_error",
                    "message": "Syntax error",
                    "severity": "error",
                    "line_number": 1
                }
            ],
            "suggestions": [],
            "corrected_code": None,
            "summary": {
                "total_observations": 0,
                "total_errors": 1,
                "total_suggestions": 0,
                "quality_score": 50
            }
        }
        
        # Apply orchestration rules
        processed = coordinator.orchestration_engine.apply_orchestration_rules(
            mock_result, "test_analysis_001"
        )
        
        assert processed is not None
        assert "orchestration" in processed
        assert processed["orchestration"]["analysis_id"] == "test_analysis_001"
        assert "quality_scores" in processed
        assert "recommendations" in processed
    
    def test_message_schema_validation(self):
        """Test A2A message schema validation"""
        from a2a_protocol.message_schema import TaskRequest, TaskResponse, AnalysisResult
        
        # Test TaskRequest
        task_request = TaskRequest(
            id="test_id",
            method="analyze_code",
            params={"code": "print('hello')", "language": "python"}
        )
        
        assert task_request.id == "test_id"
        assert task_request.method == "analyze_code"
        assert "code" in task_request.params
        
        # Test TaskResponse
        task_response = TaskResponse(
            id="test_id",
            result={"status": "completed"}
        )
        
        assert task_response.id == "test_id"
        assert task_response.result["status"] == "completed"
        
        # Test AnalysisResult
        analysis_result = AnalysisResult(
            agent_id="test_agent",
            task_id="test_task",
            status="completed",
            observations=[],
            errors=[],
            suggestions=[]
        )
        
        assert analysis_result.agent_id == "test_agent"
        assert analysis_result.task_id == "test_task"
        assert analysis_result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, coordinator, sample_code):
        """Test complete end-to-end workflow"""
        # This test would require actual remote agents running
        # For now, we'll test the coordinator's ability to handle the workflow
        
        # Test analysis configuration
        analysis_config = coordinator.get_analysis_capabilities()
        assert "syntax_check" in analysis_config
        assert "security_scan" in analysis_config
        assert "performance_analysis" in analysis_config
        
        # Test system status
        status = await coordinator.get_agent_status()
        assert "registry" in status
        assert "agents" in status
        
        # Test health check
        health = await coordinator.health_check()
        assert "status" in health
        assert health["status"] in ["healthy", "degraded"]


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
