"""
Syntax Agent

This module implements the syntax analysis remote agent for the A2A Code Review System.
Provides syntax and style analysis capabilities via the A2A protocol.
"""

from typing import Dict, Any, Optional
from agents.base.remote_agent import RemoteAgent
from a2a_protocol.message_schema import AgentCapability, AnalysisResult, TaskStatus
from analyzers.syntax_analyzer import SyntaxAnalyzer
from utils.logger import A2ALogger


class SyntaxAgent(RemoteAgent):
    """
    Remote agent for syntax and style analysis
    
    Provides comprehensive syntax analysis including:
    - Syntax error detection
    - Style and formatting checks
    - PEP 8 compliance
    - Code structure analysis
    """
    
    def __init__(self, port: int = 5001):
        """
        Initialize syntax agent
        
        Args:
            port: Port for the HTTP server
        """
        # Define agent capabilities
        capabilities = [
            AgentCapability(
                name="syntax_check",
                description="Check code syntax and identify syntax errors",
                parameters={
                    "language": "string",
                    "strict_mode": "boolean"
                }
            ),
            AgentCapability(
                name="linting",
                description="Perform code linting and style checking",
                parameters={
                    "style_guide": "string",
                    "max_line_length": "integer"
                }
            ),
            AgentCapability(
                name="style_validation",
                description="Validate code style and formatting",
                parameters={
                    "format_type": "string",
                    "auto_fix": "boolean"
                }
            )
        ]
        
        super().__init__(
            agent_id="syntax-analyzer-001",
            name="Syntax Analysis Agent",
            capabilities=capabilities,
            port=port
        )
        
        # Initialize analyzer lazily to avoid pickling issues
        self._analyzer = None
        
        # Log initialization
        self._get_logger().info("Syntax agent initialized")
    
    def _get_analyzer(self):
        """Get analyzer instance (lazy initialization to avoid pickling issues)"""
        if self._analyzer is None:
            from analyzers.syntax_analyzer import SyntaxAnalyzer
            self._analyzer = SyntaxAnalyzer()
        return self._analyzer
    
    def _get_logger(self):
        """Get logger instance (lazy initialization to avoid pickling issues)"""
        # Create a new logger instance each time to avoid pickling issues
        return A2ALogger("syntax-analyzer-001", "remote")
    
    async def analyze_code(self, task_params: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze code for syntax and style issues
        
        Args:
            task_params: Task parameters including code to analyze
            
        Returns:
            Analysis result
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
                        "message": "No code provided for analysis",
                        "severity": "error"
                    }]
                )
            
            self._get_logger().info(f"Starting syntax analysis for {language} code")
            
            # Perform analysis
            analysis_result = await self._get_analyzer().analyze_code(code, language, options)
            
            # Convert to standard format
            observations = analysis_result.get("observations", [])
            errors = analysis_result.get("errors", [])
            suggestions = analysis_result.get("suggestions", [])
            corrected_code = analysis_result.get("corrected_code")
            
            # Create analysis result
            result = self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.COMPLETED,
                observations=observations,
                errors=errors,
                suggestions=suggestions,
                corrected_code=corrected_code,
                metadata={
                    "analyzer_type": "syntax",
                    "language": language,
                    "quality_score": analysis_result.get("quality_score", 0),
                    "analysis_timestamp": analysis_result.get("metadata", {}).get("analysis_timestamp")
                }
            )
            
            self._get_logger().info(f"Syntax analysis completed with {len(errors)} errors and {len(suggestions)} suggestions")
            return result
            
        except Exception as e:
            self._get_logger().error(f"Error in syntax analysis: {e}")
            return self.create_analysis_result(
                task_id=task_params.get("task_id", "unknown"),
                status=TaskStatus.FAILED,
                errors=[{
                    "type": "analysis_error",
                    "message": f"Syntax analysis failed: {str(e)}",
                    "severity": "critical"
                }],
                metadata={"error": str(e)}
            )
    
    async def start(self) -> bool:
        """
        Start the syntax agent
        
        Returns:
            True if startup was successful
        """
        try:
            success = await super().start()
            if success:
                self._get_logger().info(f"Syntax agent started successfully on port {self.port}")
            return success
        except Exception as e:
            self._get_logger().error(f"Failed to start syntax agent: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the syntax agent
        
        Returns:
            True if shutdown was successful
        """
        try:
            success = await super().stop()
            if success:
                self._get_logger().info("Syntax agent stopped successfully")
            return success
        except Exception as e:
            self._get_logger().error(f"Failed to stop syntax agent: {e}")
            return False


# Standalone server for testing
async def main():
    """Run the syntax agent as a standalone server"""
    import asyncio
    
    agent = SyntaxAgent()
    
    try:
        await agent.start()
        print(f"Syntax agent running on port {agent.port}")
        print("Press Ctrl+C to stop")
        
        # Keep running until interrupted
        await agent.wait_for_shutdown()
        
    except KeyboardInterrupt:
        print("\nShutting down syntax agent...")
        await agent.stop()
    except Exception as e:
        print(f"Error running syntax agent: {e}")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
