"""
Test Coverage Agent

This module implements the test coverage analysis remote agent for the A2A Code Review System.
Provides test coverage analysis and quality assessment.
"""

from typing import Dict, Any, Optional
from agents.base.remote_agent import RemoteAgent
from a2a_protocol.message_schema import AgentCapability, AnalysisResult, TaskStatus
from utils.logger import A2ALogger


class TestCoverageAgent(RemoteAgent):
    """
    Remote agent for test coverage analysis
    
    Provides comprehensive test coverage analysis including:
    - Test coverage assessment
    - Test quality evaluation
    - Missing test case suggestions
    - Test structure analysis
    """
    
    def __init__(self, port: int = 5005):
        """
        Initialize test coverage agent
        
        Args:
            port: Port for the HTTP server
        """
        # Define agent capabilities
        capabilities = [
            AgentCapability(
                name="coverage_analysis",
                description="Analyze test coverage and completeness",
                parameters={
                    "coverage_threshold": "float",
                    "include_branch_coverage": "boolean"
                }
            ),
            AgentCapability(
                name="test_quality_assessment",
                description="Assess test quality and effectiveness",
                parameters={
                    "test_framework": "string",
                    "quality_metrics": "array"
                }
            ),
            AgentCapability(
                name="missing_test_suggestions",
                description="Suggest missing test cases",
                parameters={
                    "suggestion_depth": "string",
                    "include_edge_cases": "boolean"
                }
            )
        ]
        
        super().__init__(
            agent_id="test-coverage-001",
            name="Test Coverage Agent",
            capabilities=capabilities,
            port=port
        )
        
        self.logger = A2ALogger("test-coverage-001", "remote")
        
        self.logger.info("Test coverage agent initialized")
    
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code for test coverage
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Test coverage analysis result
        """
        try:
            # Extract parameters
            code = task_params.get("code", "")
            language = task_params.get("language", "python")
            options = task_params.get("options", {})
            
            if not code:
                return self.create_analysis_result(
                    task_id=task_params.get("task_id", "unknown"),
                    status=TaskStatus.FAILED,
                    errors=[{
                        "type": "validation_error",
                        "message": "No code provided for test coverage analysis",
                        "severity": "error"
                    }]
                )
            
            self.logger.info(f"Starting test coverage analysis for {language} code")
            
            # Test coverage analysis logic
            observations = []
            errors = []
            suggestions = []
            
            # Analyze test presence
            test_analysis = self._analyze_test_presence(code)
            observations.extend(test_analysis["observations"])
            suggestions.extend(test_analysis["suggestions"])
            
            # Analyze test quality
            quality_analysis = self._analyze_test_quality(code)
            observations.extend(quality_analysis["observations"])
            suggestions.extend(quality_analysis["suggestions"])
            
            # Calculate coverage score
            coverage_score = self._calculate_coverage_score(code)
            
            # Create analysis result
            result = self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.COMPLETED,
                observations=observations,
                errors=errors,
                suggestions=suggestions,
                metadata={
                    "analysis_type": "test_coverage",
                    "language": language,
                    "coverage_score": coverage_score,
                    "functions_with_tests": test_analysis["functions_with_tests"],
                    "total_functions": test_analysis["total_functions"],
                    "test_framework_detected": quality_analysis["test_framework"]
                }
            )
            
            self.logger.info(f"Test coverage analysis completed: score {coverage_score}/100")
            return result
            
        except Exception as e:
            self.logger.error(f"Test coverage analysis failed: {e}")
            return self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.FAILED,
                errors=[{
                    "type": "analysis_error",
                    "message": f"Test coverage analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )
    
    def _analyze_test_presence(self, code: str) -> Dict[str, Any]:
        """Analyze presence of tests for functions"""
        observations = []
        suggestions = []
        
        lines = code.split('\n')
        functions_with_tests = 0
        total_functions = 0
        functions = []
        
        # Find all functions
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and not line.strip().startswith('def test_'):
                total_functions += 1
                function_name = line.strip().split('(')[0].replace('def ', '')
                functions.append(function_name)
        
        # Check for test functions
        test_functions = []
        for line in lines:
            if line.strip().startswith('def test_'):
                test_name = line.strip().split('(')[0].replace('def test_', '')
                test_functions.append(test_name)
        
        # Match functions with tests
        for func in functions:
            has_test = any(func in test_func for test_func in test_functions)
            if has_test:
                functions_with_tests += 1
            else:
                observations.append({
                    "type": "missing_test",
                    "message": f"Function '{func}' lacks test coverage",
                    "severity": "warning"
                })
                
                suggestions.append({
                    "type": "test_improvement",
                    "message": f"Add test case for function '{func}'",
                    "priority": "high"
                })
        
        # Check overall test coverage
        if total_functions > 0:
            coverage_ratio = functions_with_tests / total_functions
            if coverage_ratio < 0.5:
                observations.append({
                    "type": "low_test_coverage",
                    "message": f"Low test coverage: {coverage_ratio:.1%}",
                    "severity": "warning",
                    "metric": coverage_ratio
                })
                
                suggestions.append({
                    "type": "test_improvement",
                    "message": "Consider adding more comprehensive test coverage",
                    "priority": "high"
                })
        
        return {
            "observations": observations,
            "suggestions": suggestions,
            "functions_with_tests": functions_with_tests,
            "total_functions": total_functions
        }
    
    def _analyze_test_quality(self, code: str) -> Dict[str, Any]:
        """Analyze quality of existing tests"""
        observations = []
        suggestions = []
        
        lines = code.split('\n')
        test_framework = "unknown"
        
        # Detect test framework
        if "import unittest" in code or "from unittest" in code:
            test_framework = "unittest"
        elif "import pytest" in code or "from pytest" in code:
            test_framework = "pytest"
        elif "import nose" in code or "from nose" in code:
            test_framework = "nose"
        
        # Analyze test structure
        test_functions = [line for line in lines if line.strip().startswith('def test_')]
        
        if not test_functions:
            observations.append({
                "type": "no_tests_found",
                "message": "No test functions detected",
                "severity": "error"
            })
            
            suggestions.append({
                "type": "test_improvement",
                "message": "Add test functions using def test_* naming convention",
                "priority": "high"
            })
        else:
            # Check for assertion statements
            assertion_count = sum(1 for line in lines if any(keyword in line for keyword in ["assert ", "self.assertEqual", "self.assertTrue"]))
            
            if assertion_count < len(test_functions):
                observations.append({
                    "type": "weak_test_assertions",
                    "message": f"Some tests may lack proper assertions ({assertion_count} assertions for {len(test_functions)} tests)",
                    "severity": "warning"
                })
                
                suggestions.append({
                    "type": "test_improvement",
                    "message": "Ensure all tests have proper assertion statements",
                    "priority": "medium"
                })
        
        return {
            "observations": observations,
            "suggestions": suggestions,
            "test_framework": test_framework
        }
    
    def _calculate_coverage_score(self, code: str) -> int:
        """Calculate overall test coverage score"""
        try:
            score = 100
            
            lines = code.split('\n')
            
            # Count functions and tests
            functions = [line for line in lines if line.strip().startswith('def ') and not line.strip().startswith('def test_')]
            test_functions = [line for line in lines if line.strip().startswith('def test_')]
            
            if not functions:
                return 100  # No functions to test
            
            # Calculate coverage ratio
            coverage_ratio = len(test_functions) / len(functions) if functions else 0
            
            # Deduct points based on coverage
            if coverage_ratio < 0.5:
                score -= 50
            elif coverage_ratio < 0.8:
                score -= 30
            elif coverage_ratio < 1.0:
                score -= 10
            
            # Check for test framework
            if not any(framework in code for framework in ["unittest", "pytest", "nose"]):
                score -= 20
            
            # Check for assertions
            assertion_count = sum(1 for line in lines if any(keyword in line for keyword in ["assert ", "self.assertEqual", "self.assertTrue"]))
            if assertion_count == 0:
                score -= 30
            
            return max(0, score)
            
        except:
            return 50  # Default score if analysis fails
