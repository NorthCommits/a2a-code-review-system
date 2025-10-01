"""
Security Agent

This module implements the security analysis remote agent for the A2A Code Review System.
Provides security vulnerability detection and analysis capabilities.
"""

from typing import Dict, Any, Optional
from agents.base.remote_agent import RemoteAgent
from a2a_protocol.message_schema import AgentCapability, AnalysisResult, TaskStatus
from utils.logger import A2ALogger


class SecurityAgent(RemoteAgent):
    """
    Remote agent for security analysis
    
    Provides comprehensive security analysis including:
    - Vulnerability detection
    - SQL injection scanning
    - XSS detection
    - Security best practices
    """
    
    def __init__(self, port: int = 5002):
        """
        Initialize security agent
        
        Args:
            port: Port for the HTTP server
        """
        # Define agent capabilities
        capabilities = [
            AgentCapability(
                name="vulnerability_scan",
                description="Scan for security vulnerabilities",
                parameters={
                    "scan_depth": "string",
                    "include_patterns": "array"
                }
            ),
            AgentCapability(
                name="sql_injection_check",
                description="Check for SQL injection vulnerabilities",
                parameters={
                    "database_type": "string",
                    "query_analysis": "boolean"
                }
            ),
            AgentCapability(
                name="xss_detection",
                description="Detect Cross-Site Scripting vulnerabilities",
                parameters={
                    "context_analysis": "boolean",
                    "sanitization_check": "boolean"
                }
            )
        ]
        
        super().__init__(
            agent_id="security-scanner-001",
            name="Security Scanner Agent",
            capabilities=capabilities,
            port=port
        )
        
        self.logger = A2ALogger("security-scanner-001", "remote")
        
        self.logger.info("Security agent initialized")
    
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code for security vulnerabilities
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Security analysis result
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
                        "message": "No code provided for security analysis",
                        "severity": "error"
                    }]
                )
            
            self.logger.info(f"Starting security analysis for {language} code")
            
            # Security analysis logic
            observations = []
            errors = []
            suggestions = []
            
            # Check for common security issues
            security_patterns = [
                ("sql_injection", ["SELECT", "INSERT", "UPDATE", "DELETE"], "Potential SQL injection vulnerability"),
                ("xss", ["document.write", "innerHTML", "eval("], "Potential XSS vulnerability"),
                ("hardcoded_secrets", ["password", "secret", "key", "token"], "Hardcoded credentials detected"),
                ("unsafe_eval", ["eval(", "exec(", "compile("], "Unsafe code execution detected"),
                ("file_operations", ["open(", "file(", "os.system"], "Potentially unsafe file operations")
            ]
            
            for pattern_type, keywords, message in security_patterns:
                for keyword in keywords:
                    if keyword.lower() in code.lower():
                        observations.append({
                            "type": pattern_type,
                            "message": f"{message} - found '{keyword}'",
                            "severity": "warning",
                            "line": self._find_line_number(code, keyword)
                        })
            
            # Security best practices suggestions
            if "import hashlib" not in code and "password" in code.lower():
                suggestions.append({
                    "type": "security_improvement",
                    "message": "Consider using proper password hashing with hashlib",
                    "priority": "high"
                })
            
            if "import ssl" not in code and ("http://" in code or "requests.get" in code):
                suggestions.append({
                    "type": "security_improvement", 
                    "message": "Consider using HTTPS for secure communications",
                    "priority": "medium"
                })
            
            # Create analysis result
            result = self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.COMPLETED,
                observations=observations,
                errors=errors,
                suggestions=suggestions,
                metadata={
                    "analysis_type": "security",
                    "language": language,
                    "patterns_checked": len(security_patterns),
                    "vulnerabilities_found": len(observations)
                }
            )
            
            self.logger.info(f"Security analysis completed: {len(observations)} issues found")
            return result
            
        except Exception as e:
            self.logger.error(f"Security analysis failed: {e}")
            return self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.FAILED,
                errors=[{
                    "type": "analysis_error",
                    "message": f"Security analysis failed: {str(e)}",
                    "severity": "error"
                }]
            )
    
    def _find_line_number(self, code: str, keyword: str) -> Optional[int]:
        """Find line number where keyword appears"""
        try:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if keyword.lower() in line.lower():
                    return i
            return None
        except:
            return None
