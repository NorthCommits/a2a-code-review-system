"""
Orchestration Engine

This module implements workflow orchestration logic for the coordinator agent.
Manages task dependencies, execution order, and result processing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionStrategy(str, Enum):
    """Execution strategy enumeration"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    PIPELINE = "pipeline"


class OrchestrationEngine:
    """
    Orchestration engine for managing analysis workflows
    
    Handles task dependencies, execution strategies, and result processing
    for complex multi-agent analysis workflows.
    """
    
    def __init__(self):
        """Initialize orchestration engine"""
        self.logger = get_logger(__name__)
        
        # Workflow configuration
        self.execution_strategy = ExecutionStrategy.PARALLEL
        self.task_dependencies = self._define_task_dependencies()
        self.result_processing_rules = self._define_result_processing_rules()
        
        self.logger.info("Initialized Orchestration Engine")
    
    def _define_task_dependencies(self) -> Dict[str, List[str]]:
        """
        Define task dependencies for analysis workflows
        
        Returns:
            Dictionary mapping tasks to their dependencies
        """
        return {
            "syntax_check": [],  # No dependencies
            "security_scan": [],  # No dependencies
            "performance_analysis": ["syntax_check"],  # Needs valid syntax
            "documentation_check": [],  # No dependencies
            "test_coverage": ["syntax_check"]  # Needs valid syntax
        }
    
    def _define_result_processing_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Define result processing rules for different analysis types
        
        Returns:
            Dictionary of processing rules
        """
        return {
            "syntax_check": {
                "critical_errors": ["syntax_error", "indentation_error"],
                "auto_fix": True,
                "stop_on_critical": True
            },
            "security_scan": {
                "critical_errors": ["sql_injection", "xss_vulnerability", "hardcoded_secret"],
                "auto_fix": False,
                "stop_on_critical": False
            },
            "performance_analysis": {
                "critical_errors": ["memory_leak", "infinite_loop"],
                "auto_fix": False,
                "stop_on_critical": False
            },
            "documentation_check": {
                "critical_errors": [],
                "auto_fix": True,
                "stop_on_critical": False
            },
            "test_coverage": {
                "critical_errors": [],
                "auto_fix": False,
                "stop_on_critical": False
            }
        }
    
    def apply_orchestration_rules(
        self, 
        aggregated_result: Dict[str, Any], 
        analysis_id: str
    ) -> Dict[str, Any]:
        """
        Apply orchestration rules to aggregated results
        
        Args:
            aggregated_result: Aggregated analysis results
            analysis_id: Analysis identifier
            
        Returns:
            Processed results with orchestration applied
        """
        try:
            self.logger.info(f"Applying orchestration rules for analysis: {analysis_id}")
            
            # Create a copy of the result to modify
            processed_result = aggregated_result.copy()
            
            # Apply critical error handling
            processed_result = self._handle_critical_errors(processed_result)
            
            # Apply result prioritization
            processed_result = self._prioritize_results(processed_result)
            
            # Apply quality scoring
            processed_result = self._calculate_quality_scores(processed_result)
            
            # Apply recommendations
            processed_result = self._generate_recommendations(processed_result)
            
            # Add orchestration metadata
            processed_result["orchestration"] = {
                "analysis_id": analysis_id,
                "execution_strategy": self.execution_strategy.value,
                "processed_at": datetime.utcnow().isoformat(),
                "rules_applied": list(self.result_processing_rules.keys())
            }
            
            self.logger.info("Successfully applied orchestration rules")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Error applying orchestration rules: {e}")
            return aggregated_result
    
    def _handle_critical_errors(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle critical errors based on orchestration rules
        
        Args:
            result: Analysis result
            
        Returns:
            Result with critical error handling applied
        """
        try:
            errors = result.get("errors", [])
            critical_errors = []
            non_critical_errors = []
            
            # Categorize errors by criticality
            for error in errors:
                error_type = error.get("type", "")
                
                # Check if this is a critical error for any analysis type
                is_critical = False
                for analysis_type, rules in self.result_processing_rules.items():
                    if error_type in rules.get("critical_errors", []):
                        is_critical = True
                        break
                
                if is_critical:
                    critical_errors.append(error)
                else:
                    non_critical_errors.append(error)
            
            # Update result with categorized errors
            result["errors"] = {
                "critical": critical_errors,
                "non_critical": non_critical_errors
            }
            
            # Add critical error summary
            result["critical_error_summary"] = {
                "count": len(critical_errors),
                "types": list(set(error.get("type", "") for error in critical_errors)),
                "requires_immediate_attention": len(critical_errors) > 0
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling critical errors: {e}")
            return result
    
    def _prioritize_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prioritize results based on importance and impact
        
        Args:
            result: Analysis result
            
        Returns:
            Result with prioritization applied
        """
        try:
            # Prioritize errors by severity and type
            errors = result.get("errors", {})
            if isinstance(errors, list):
                # Convert to dict format if needed
                errors = {"critical": errors, "non_critical": []}
            
            # Sort critical errors by severity
            if "critical" in errors:
                errors["critical"].sort(
                    key=lambda x: (
                        self._get_error_priority(x.get("type", "")),
                        x.get("line_number", 0)
                    )
                )
            
            # Sort non-critical errors by severity
            if "non_critical" in errors:
                errors["non_critical"].sort(
                    key=lambda x: (
                        self._get_error_priority(x.get("type", "")),
                        x.get("line_number", 0)
                    )
                )
            
            result["errors"] = errors
            
            # Prioritize suggestions by impact
            suggestions = result.get("suggestions", [])
            suggestions.sort(
                key=lambda x: (
                    x.get("priority", 5),
                    x.get("impact", "low")
                ),
                reverse=True
            )
            result["suggestions"] = suggestions
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error prioritizing results: {e}")
            return result
    
    def _calculate_quality_scores(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate quality scores based on analysis results
        
        Args:
            result: Analysis result
            
        Returns:
            Result with quality scores added
        """
        try:
            errors = result.get("errors", {})
            observations = result.get("observations", [])
            suggestions = result.get("suggestions", [])
            
            # Calculate base quality score
            total_issues = 0
            critical_issues = 0
            
            if isinstance(errors, dict):
                critical_errors = errors.get("critical", [])
                non_critical_errors = errors.get("non_critical", [])
                total_issues += len(critical_errors) + len(non_critical_errors)
                critical_issues += len(critical_errors)
            else:
                total_issues += len(errors)
            
            # Add observations to total issues
            total_issues += len(observations)
            
            # Calculate component scores
            syntax_score = self._calculate_syntax_score(errors)
            security_score = self._calculate_security_score(errors)
            performance_score = self._calculate_performance_score(observations)
            documentation_score = self._calculate_documentation_score(observations)
            test_score = self._calculate_test_score(observations)
            
            # Calculate overall quality score
            component_scores = [syntax_score, security_score, performance_score, documentation_score, test_score]
            overall_score = sum(component_scores) / len(component_scores) if component_scores else 0
            
            # Apply penalty for critical issues
            if critical_issues > 0:
                overall_score *= max(0.1, 1 - (critical_issues * 0.2))
            
            result["quality_scores"] = {
                "overall": round(overall_score, 2),
                "syntax": syntax_score,
                "security": security_score,
                "performance": performance_score,
                "documentation": documentation_score,
                "test_coverage": test_score,
                "total_issues": total_issues,
                "critical_issues": critical_issues
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating quality scores: {e}")
            return result
    
    def _generate_recommendations(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate actionable recommendations based on analysis results
        
        Args:
            result: Analysis result
            
        Returns:
            Result with recommendations added
        """
        try:
            recommendations = []
            quality_scores = result.get("quality_scores", {})
            
            # Generate recommendations based on quality scores
            if quality_scores.get("syntax", 100) < 80:
                recommendations.append({
                    "type": "syntax",
                    "priority": "high",
                    "message": "Fix syntax errors to improve code quality",
                    "action": "review_and_fix_syntax_errors"
                })
            
            if quality_scores.get("security", 100) < 70:
                recommendations.append({
                    "type": "security",
                    "priority": "critical",
                    "message": "Address security vulnerabilities immediately",
                    "action": "review_security_issues"
                })
            
            if quality_scores.get("performance", 100) < 60:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "message": "Optimize code for better performance",
                    "action": "review_performance_suggestions"
                })
            
            if quality_scores.get("documentation", 100) < 50:
                recommendations.append({
                    "type": "documentation",
                    "priority": "low",
                    "message": "Improve code documentation",
                    "action": "add_documentation"
                })
            
            if quality_scores.get("test_coverage", 100) < 60:
                recommendations.append({
                    "type": "testing",
                    "priority": "medium",
                    "message": "Increase test coverage",
                    "action": "add_more_tests"
                })
            
            # Add general recommendations
            if quality_scores.get("overall", 100) < 50:
                recommendations.append({
                    "type": "general",
                    "priority": "high",
                    "message": "Overall code quality needs significant improvement",
                    "action": "comprehensive_code_review"
                })
            
            result["recommendations"] = recommendations
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return result
    
    def _get_error_priority(self, error_type: str) -> int:
        """Get priority for error type (lower number = higher priority)"""
        priority_map = {
            "syntax_error": 1,
            "indentation_error": 1,
            "sql_injection": 2,
            "xss_vulnerability": 2,
            "hardcoded_secret": 2,
            "memory_leak": 3,
            "infinite_loop": 3,
            "performance_bottleneck": 4,
            "missing_docstring": 5,
            "poor_naming": 5,
            "missing_test": 6
        }
        return priority_map.get(error_type, 10)
    
    def _calculate_syntax_score(self, errors: Any) -> float:
        """Calculate syntax quality score"""
        if isinstance(errors, dict):
            critical_errors = errors.get("critical", [])
            non_critical_errors = errors.get("non_critical", [])
            syntax_errors = [e for e in critical_errors + non_critical_errors 
                           if e.get("type") in ["syntax_error", "indentation_error"]]
        else:
            syntax_errors = [e for e in errors if e.get("type") in ["syntax_error", "indentation_error"]]
        
        return max(0, 100 - len(syntax_errors) * 20)
    
    def _calculate_security_score(self, errors: Any) -> float:
        """Calculate security quality score"""
        if isinstance(errors, dict):
            critical_errors = errors.get("critical", [])
            non_critical_errors = errors.get("non_critical", [])
            security_errors = [e for e in critical_errors + non_critical_errors 
                             if e.get("type") in ["sql_injection", "xss_vulnerability", "hardcoded_secret"]]
        else:
            security_errors = [e for e in errors if e.get("type") in ["sql_injection", "xss_vulnerability", "hardcoded_secret"]]
        
        return max(0, 100 - len(security_errors) * 30)
    
    def _calculate_performance_score(self, observations: List[Dict[str, Any]]) -> float:
        """Calculate performance quality score"""
        performance_issues = [obs for obs in observations if obs.get("type") == "performance_issue"]
        return max(0, 100 - len(performance_issues) * 10)
    
    def _calculate_documentation_score(self, observations: List[Dict[str, Any]]) -> float:
        """Calculate documentation quality score"""
        doc_issues = [obs for obs in observations if obs.get("type") in ["missing_docstring", "poor_naming"]]
        return max(0, 100 - len(doc_issues) * 5)
    
    def _calculate_test_score(self, observations: List[Dict[str, Any]]) -> float:
        """Calculate test coverage quality score"""
        test_issues = [obs for obs in observations if obs.get("type") == "missing_test"]
        return max(0, 100 - len(test_issues) * 15)
    
    def get_execution_strategy(self) -> ExecutionStrategy:
        """Get current execution strategy"""
        return self.execution_strategy
    
    def set_execution_strategy(self, strategy: ExecutionStrategy):
        """
        Set execution strategy
        
        Args:
            strategy: New execution strategy
        """
        self.execution_strategy = strategy
        self.logger.info(f"Execution strategy changed to: {strategy.value}")
    
    def get_task_dependencies(self) -> Dict[str, List[str]]:
        """Get task dependencies configuration"""
        return self.task_dependencies.copy()
    
    def get_result_processing_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get result processing rules"""
        return self.result_processing_rules.copy()
