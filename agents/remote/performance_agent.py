"""
Performance Agent

This module implements the performance analysis remote agent for the A2A Code Review System.
Provides code performance analysis and optimization suggestions.
"""

from typing import Dict, Any, Optional
from agents.base.remote_agent import RemoteAgent
from a2a_protocol.message_schema import AgentCapability, AnalysisResult, TaskStatus
from utils.logger import A2ALogger


class PerformanceAgent(RemoteAgent):
    """
    Remote agent for performance analysis
    
    Provides comprehensive performance analysis including:
    - Code complexity analysis
    - Performance optimization suggestions
    - Memory usage analysis
    - Algorithm efficiency assessment
    """
    
    def __init__(self, port: int = 5003):
        """
        Initialize performance agent
        
        Args:
            port: Port for the HTTP server
        """
        # Define agent capabilities
        capabilities = [
            AgentCapability(
                name="complexity_analysis",
                description="Analyze code complexity and performance",
                parameters={
                    "complexity_threshold": "integer",
                    "include_nested": "boolean"
                }
            ),
            AgentCapability(
                name="optimization_suggestions",
                description="Suggest performance optimizations",
                parameters={
                    "optimization_level": "string",
                    "include_benchmarks": "boolean"
                }
            ),
            AgentCapability(
                name="memory_analysis",
                description="Analyze memory usage patterns",
                parameters={
                    "track_allocation": "boolean",
                    "leak_detection": "boolean"
                }
            )
        ]
        
        super().__init__(
            agent_id="performance-analyzer-001",
            name="Performance Analyzer Agent",
            capabilities=capabilities,
            port=port
        )
        
        # Logger will be initialized when needed to avoid pickling issues
        pass
    
    def _get_logger(self):
        """Get logger instance (lazy initialization to avoid pickling issues)"""
        # Create a new logger instance each time to avoid pickling issues
        return A2ALogger("performance-analyzer-001", "remote")
    
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code for performance issues
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Performance analysis result
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
                        "message": "No code provided for performance analysis",
                        "severity": "error"
                    }]
                )
            
            self._get_logger().info(f"Starting performance analysis for {language} code")
            
            # Performance analysis logic
            observations = []
            errors = []
            suggestions = []
            
            # Analyze code complexity
            complexity_score = self._calculate_complexity(code)
            if complexity_score > 10:
                observations.append({
                    "type": "high_complexity",
                    "message": f"High code complexity detected (score: {complexity_score})",
                    "severity": "warning",
                    "metric": complexity_score
                })
            
            # Check for performance anti-patterns
            performance_patterns = [
                ("nested_loops", ["for", "while"], "Nested loops detected - consider optimization"),
                ("inefficient_string", ["+=", "string concatenation"], "Inefficient string operations detected"),
                ("global_variables", ["global "], "Global variables may impact performance"),
                ("recursive_calls", ["def ", "return"], "Recursive functions may cause stack overflow"),
                ("large_data_structures", ["list(", "dict(", "set("], "Large data structures may impact memory")
            ]
            
            for pattern_type, keywords, message in performance_patterns:
                count = sum(code.count(keyword) for keyword in keywords)
                if count > 3:  # Threshold for concern
                    observations.append({
                        "type": pattern_type,
                        "message": f"{message} (count: {count})",
                        "severity": "info",
                        "count": count
                    })
            
            # Performance optimization suggestions
            if "for" in code and "range(" in code:
                suggestions.append({
                    "type": "optimization",
                    "message": "Consider using list comprehensions for better performance",
                    "priority": "medium"
                })
            
            if "import json" in code and "json.loads" in code:
                suggestions.append({
                    "type": "optimization",
                    "message": "Consider caching JSON parsing results for repeated operations",
                    "priority": "low"
                })
            
            # Memory usage analysis
            memory_issues = []
            if "import" in code:
                import_count = code.count("import")
                if import_count > 10:
                    memory_issues.append({
                        "type": "memory_usage",
                        "message": f"High number of imports ({import_count}) may impact memory usage",
                        "severity": "info"
                    })
            
            # Create analysis result
            result = self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.COMPLETED,
                observations=observations + memory_issues,
                errors=errors,
                suggestions=suggestions,
                metadata={
                    "analysis_type": "performance",
                    "language": language,
                    "complexity_score": complexity_score,
                    "performance_issues": len(observations),
                    "lines_of_code": len(code.split('\n'))
                }
            )
            
            self._get_logger().info(f"Performance analysis completed: {len(observations)} issues found")
            return result
            
        except Exception as e:
            self._get_logger().error(f"Performance analysis failed: {e}")
            return self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.FAILED,
                errors=[{
                    "type": "analysis_error",
                    "message": f"Performance analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )
    
    def _calculate_complexity(self, code: str) -> int:
        """Calculate basic code complexity score"""
        try:
            complexity = 0
            
            # Count control structures
            complexity += code.count("if ")
            complexity += code.count("elif ")
            complexity += code.count("for ")
            complexity += code.count("while ")
            complexity += code.count("try:")
            complexity += code.count("except ")
            complexity += code.count("with ")
            
            # Count function definitions
            complexity += code.count("def ")
            
            # Count nested structures (basic estimation)
            lines = code.split('\n')
            max_indentation = 0
            for line in lines:
                if line.strip():
                    indentation = len(line) - len(line.lstrip())
                    max_indentation = max(max_indentation, indentation)
            
            complexity += max_indentation // 4  # Assuming 4-space indentation
            
            return complexity
            
        except:
            return 0
