"""
Documentation Agent

This module implements the documentation analysis remote agent for the A2A Code Review System.
Provides documentation quality assessment and suggestions.
"""

from typing import Dict, Any, Optional
from agents.base.remote_agent import RemoteAgent
from a2a_protocol.message_schema import AgentCapability, AnalysisResult, TaskStatus
from utils.logger import A2ALogger


class DocumentationAgent(RemoteAgent):
    """
    Remote agent for documentation analysis
    
    Provides comprehensive documentation analysis including:
    - Docstring validation
    - Comment analysis
    - Readability assessment
    - Documentation completeness
    """
    
    def __init__(self, port: int = 5004):
        """
        Initialize documentation agent
        
        Args:
            port: Port for the HTTP server
        """
        # Define agent capabilities
        capabilities = [
            AgentCapability(
                name="docstring_validation",
                description="Validate docstring presence and format",
                parameters={
                    "docstring_style": "string",
                    "require_examples": "boolean"
                }
            ),
            AgentCapability(
                name="comment_analysis",
                description="Analyze comment quality and coverage",
                parameters={
                    "min_comment_density": "float",
                    "check_clarity": "boolean"
                }
            ),
            AgentCapability(
                name="readability_assessment",
                description="Assess code readability and naming",
                parameters={
                    "naming_convention": "string",
                    "readability_threshold": "float"
                }
            )
        ]
        
        super().__init__(
            agent_id="documentation-agent-001",
            name="Documentation Quality Agent",
            capabilities=capabilities,
            port=port
        )
        
        self.logger = A2ALogger("documentation-agent-001", "remote")
        
        self.logger.info("Documentation agent initialized")
    
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code for documentation quality
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Documentation analysis result
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
                        "message": "No code provided for documentation analysis",
                        "severity": "error"
                    }]
                )
            
            self.logger.info(f"Starting documentation analysis for {language} code")
            
            # Documentation analysis logic
            observations = []
            errors = []
            suggestions = []
            
            # Analyze docstrings
            docstring_analysis = self._analyze_docstrings(code)
            observations.extend(docstring_analysis["observations"])
            suggestions.extend(docstring_analysis["suggestions"])
            
            # Analyze comments
            comment_analysis = self._analyze_comments(code)
            observations.extend(comment_analysis["observations"])
            suggestions.extend(comment_analysis["suggestions"])
            
            # Analyze readability
            readability_analysis = self._analyze_readability(code)
            observations.extend(readability_analysis["observations"])
            suggestions.extend(readability_analysis["suggestions"])
            
            # Calculate documentation score
            doc_score = self._calculate_documentation_score(code)
            
            # Create analysis result
            result = self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.COMPLETED,
                observations=observations,
                errors=errors,
                suggestions=suggestions,
                metadata={
                    "analysis_type": "documentation",
                    "language": language,
                    "documentation_score": doc_score,
                    "functions_with_docstrings": docstring_analysis["functions_with_docstrings"],
                    "total_functions": docstring_analysis["total_functions"],
                    "comment_density": comment_analysis["comment_density"]
                }
            )
            
            self.logger.info(f"Documentation analysis completed: score {doc_score}/100")
            return result
            
        except Exception as e:
            self.logger.error(f"Documentation analysis failed: {e}")
            return self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.FAILED,
                errors=[{
                    "type": "analysis_error",
                    "message": f"Documentation analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )
    
    def _analyze_docstrings(self, code: str) -> Dict[str, Any]:
        """Analyze docstring presence and quality"""
        observations = []
        suggestions = []
        
        lines = code.split('\n')
        functions_with_docstrings = 0
        total_functions = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                total_functions += 1
                function_name = line.strip().split('(')[0].replace('def ', '')
                
                # Check if function has docstring
                has_docstring = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if '"""' in lines[j] or "'''" in lines[j]:
                        has_docstring = True
                        break
                
                if has_docstring:
                    functions_with_docstrings += 1
                else:
                    observations.append({
                        "type": "missing_docstring",
                        "message": f"Function '{function_name}' lacks docstring",
                        "severity": "warning",
                        "line": i + 1
                    })
                    
                    suggestions.append({
                        "type": "documentation_improvement",
                        "message": f"Add docstring to function '{function_name}'",
                        "priority": "medium"
                    })
        
        return {
            "observations": observations,
            "suggestions": suggestions,
            "functions_with_docstrings": functions_with_docstrings,
            "total_functions": total_functions
        }
    
    def _analyze_comments(self, code: str) -> Dict[str, Any]:
        """Analyze comment quality and coverage"""
        observations = []
        suggestions = []
        
        lines = code.split('\n')
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        
        comment_density = len(comment_lines) / len(code_lines) if code_lines else 0
        
        if comment_density < 0.1:  # Less than 10% comments
            observations.append({
                "type": "low_comment_density",
                "message": f"Low comment density: {comment_density:.1%}",
                "severity": "info",
                "metric": comment_density
            })
            
            suggestions.append({
                "type": "documentation_improvement",
                "message": "Consider adding more comments to explain complex logic",
                "priority": "low"
            })
        
        return {
            "observations": observations,
            "suggestions": suggestions,
            "comment_density": comment_density
        }
    
    def _analyze_readability(self, code: str) -> Dict[str, Any]:
        """Analyze code readability and naming conventions"""
        observations = []
        suggestions = []
        
        lines = code.split('\n')
        
        # Check for unclear variable names
        unclear_names = []
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                # Extract variable names
                var_part = line.split('=')[0].strip()
                if var_part and len(var_part) < 3:
                    unclear_names.append(var_part)
        
        if unclear_names:
            observations.append({
                "type": "unclear_naming",
                "message": f"Unclear variable names detected: {', '.join(unclear_names)}",
                "severity": "warning"
            })
            
            suggestions.append({
                "type": "readability_improvement",
                "message": "Use descriptive variable names instead of single letters",
                "priority": "medium"
            })
        
        return {
            "observations": observations,
            "suggestions": suggestions
        }
    
    def _calculate_documentation_score(self, code: str) -> int:
        """Calculate overall documentation quality score"""
        try:
            score = 100
            
            # Check for docstrings
            if 'def ' in code and '"""' not in code and "'''" not in code:
                score -= 30
            
            # Check for comments
            lines = code.split('\n')
            code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
            comment_lines = [line for line in lines if line.strip().startswith('#')]
            
            comment_ratio = len(comment_lines) / len(code_lines) if code_lines else 0
            if comment_ratio < 0.1:
                score -= 20
            
            # Check for unclear naming
            unclear_count = sum(1 for line in lines if '=' in line and len(line.split('=')[0].strip()) < 3)
            if unclear_count > 0:
                score -= min(20, unclear_count * 5)
            
            return max(0, score)
            
        except:
            return 50  # Default score if analysis fails
