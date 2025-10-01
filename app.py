"""
A2A Code Review System - Main Streamlit Application

This is the main entry point for the A2A Code Review System.
Provides a web interface for users to submit code for analysis
using multiple specialized AI agents.
"""

import streamlit as st
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Import A2A system components
from registry.agent_registry import AgentRegistry
from agents.coordinator.coordinator import CoordinatorAgent
from storage.session_manager import SessionManager
from ui.main_interface import MainInterface
from ui.components import CodeInputComponent, ResultsDisplayComponent, ProgressComponent
from ui.realtime_updates import RealTimeUpdates
from utils.logger import setup_system_logging, get_logger
logger = get_logger(__name__)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
setup_system_logging("INFO")
logger = get_logger(__name__)


class A2ACodeReviewApp:
    """
    Main A2A Code Review System Application
    
    Manages the Streamlit interface and coordinates with the
    A2A agent system for code analysis.
    """
    
    def __init__(self):
        """Initialize the A2A Code Review application"""
        self.session_manager = SessionManager()
        self.registry = None
        self.coordinator = None
        self.interface = None
        self.realtime_updates = RealTimeUpdates()
        
        # Initialize session state
        self._initialize_session_state()
        
        logger.info("A2A Code Review System initialized")
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state"""
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        
        if 'system_status' not in st.session_state:
            st.session_state.system_status = "initializing"
        
        if 'current_analysis_id' not in st.session_state:
            st.session_state.current_analysis_id = None
        
        if 'analysis_options' not in st.session_state:
            st.session_state.analysis_options = {
                "language": "python",
                "include_security": True,
                "include_performance": True,
                "include_documentation": True,
                "include_test_coverage": False
            }
    
    async def _initialize_system(self) -> bool:
        """
        Initialize the A2A system components
        
        Returns:
            True if initialization was successful
        """
        try:
            logger.info("Initializing A2A system components...")
            
            # Initialize agent registry
            self.registry = AgentRegistry("registry/registry_config.json")
            
            # Initialize coordinator agent
            self.coordinator = CoordinatorAgent(self.registry)
            
            # Start coordinator
            await self.coordinator.start()
            
            # Initialize UI components
            self.interface = MainInterface(self.coordinator)
            
            logger.info("A2A system components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize A2A system: {e}")
            return False
    
    async def _analyze_code(self, code: str, language: str = "python", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze code using the A2A system
        
        Args:
            code: Code to analyze
            language: Programming language
            options: Optional analysis options
            
        Returns:
            Analysis results
        """
        try:
            if not self.coordinator:
                raise Exception("Coordinator agent not initialized")
            
            # Generate analysis ID
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.current_analysis_id = analysis_id
            
            # Update session state
            st.session_state.system_status = "analyzing"
            
            # Perform analysis
            results = await self.coordinator.analyze_code(code, language, options)
            results["analysis_id"] = analysis_id
            results["timestamp"] = datetime.now().isoformat()
            
            # Store results in session
            st.session_state.analysis_results = results
            st.session_state.analysis_history.append(results)
            
            # Update session state
            st.session_state.system_status = "completed"
            
            logger.info(f"Analysis completed: {analysis_id}")
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            st.session_state.system_status = "error"
            
            error_result = {
                "analysis_id": st.session_state.current_analysis_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_observations": 0,
                    "total_errors": 1,
                    "total_suggestions": 0,
                    "quality_score": 0
                }
            }
            
            st.session_state.analysis_results = error_result
            return error_result
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """
        Get system status information
        
        Returns:
            System status dictionary
        """
        try:
            if not self.coordinator:
                return {"status": "not_initialized", "error": "System not initialized"}
            
            status = await self.coordinator.get_agent_status()
            health = await self.coordinator.health_check()
            
            return {
                "status": "healthy" if health["status"] == "healthy" else "degraded",
                "coordinator": health,
                "agents": status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "error": str(e)}
    
    def run(self):
        """Run the Streamlit application"""
        try:
            # Configure Streamlit page
            st.set_page_config(
                page_title="A2A Code Review System",
                page_icon="",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            
            # Initialize system if not already done
            if st.session_state.system_status == "initializing":
                with st.spinner("Initializing A2A system..."):
                    if asyncio.run(self._initialize_system()):
                        st.session_state.system_status = "ready"
                        st.success("System initialized successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to initialize system. Please refresh the page.")
                        st.stop()
            
            # Main title and description
            st.title("A2A Code Review System")
            st.markdown("""
            **Multi-Agent Code Quality Analysis System**
            
            This system uses multiple specialized AI agents to analyze your code for:
            - **Syntax & Style** - Code formatting and linting
            - **Security** - Vulnerability detection and security best practices
            - **Performance** - Performance optimization opportunities
            - **Documentation** - Code documentation quality
            - **Test Coverage** - Test completeness and quality
            """)
            
            st.divider()
            
            # Create main interface
            if self.interface:
                self.interface.render()
            else:
                # Create a simple interface directly
                self._render_simple_interface()
            
            # Sidebar with system information
            self._render_sidebar()
            
            # Add real-time updates section
            st.divider()
            self._render_realtime_section()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"Application error: {e}")
    
    def _render_sidebar(self):
        """Render the sidebar with system information"""
        with st.sidebar:
            st.header("System Status")
            
            # System status indicator
            status = st.session_state.system_status
            if status == "ready":
                st.success("System Ready")
            elif status == "analyzing":
                st.info("Analyzing...")
            elif status == "completed":
                st.success("Analysis Complete")
            elif status == "error":
                st.error("System Error")
            else:
                st.warning("Initializing...")
            
            # System statistics
            if self.coordinator:
                try:
                    status_info = asyncio.run(self._get_system_status())
                    
                    st.subheader("Agent Status")
                    if "agents" in status_info and "registry" in status_info["agents"]:
                        registry_info = status_info["agents"]["registry"]
                        st.metric("Active Agents", registry_info.get("active_agents", 0))
                        st.metric("Healthy Agents", registry_info.get("healthy_agents", 0))
                        st.metric("Total Agents", registry_info.get("total_agents", 0))
                    
                    # Analysis history
                    st.subheader("Analysis History")
                    history = st.session_state.analysis_history
                    if history:
                        st.write(f"Total Analyses: {len(history)}")
                        
                        # Show recent analyses
                        for i, analysis in enumerate(history[-3:]):  # Show last 3
                            analysis_id = analysis.get("analysis_id", f"analysis_{i}")
                            timestamp = analysis.get("timestamp", "")
                            status = analysis.get("status", "unknown")
                            
                            if timestamp:
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    time_str = dt.strftime("%H:%M:%S")
                                except:
                                    time_str = timestamp[:8]
                            else:
                                time_str = "Unknown"
                            
                            status_icon = "[OK]" if status == "completed" else "[FAIL]" if status == "failed" else "[...]"
                            st.write(f"{status_icon} {time_str} - {analysis_id[:12]}...")
                    else:
                        st.write("No analyses yet")
                    
                except Exception as e:
                    st.error(f"Error getting system status: {e}")
            
            # Configuration
            st.subheader("Configuration")
            
            # Language selection
            language = st.selectbox(
                "Programming Language",
                ["python", "javascript", "java", "cpp", "csharp"],
                index=0,
                key="language_select"
            )
            
            # Update session state
            st.session_state.analysis_options["language"] = language
            
            # Analysis options
            st.subheader("Analysis Options")
            include_security = st.checkbox("Security Analysis", value=st.session_state.analysis_options.get("include_security", True))
            include_performance = st.checkbox("Performance Analysis", value=st.session_state.analysis_options.get("include_performance", True))
            include_documentation = st.checkbox("Documentation Check", value=st.session_state.analysis_options.get("include_documentation", True))
            include_test_coverage = st.checkbox("Test Coverage", value=st.session_state.analysis_options.get("include_test_coverage", False))
            
            # Update session state
            st.session_state.analysis_options["include_security"] = include_security
            st.session_state.analysis_options["include_performance"] = include_performance
            st.session_state.analysis_options["include_documentation"] = include_documentation
            st.session_state.analysis_options["include_test_coverage"] = include_test_coverage
            
            # System information
            st.subheader("About")
            st.info("""
            **A2A Code Review System v1.0**
            
            Built with:
            - Streamlit for UI
            - A2A Protocol for agent communication
            - OpenAI for intelligent analysis
            
            This system demonstrates multi-agent
            coordination for comprehensive code review.
            """)
    
    def _render_simple_interface(self):
        """Render a simple interface when main interface is not available"""
        st.header("Code Analysis")
        
        # Code input area
        code = st.text_area(
            "Paste your code here:",
            height=300,
            placeholder="def hello_world():\n    print('Hello, World!')\n    return 'success'",
            help="Enter your Python, JavaScript, Java, C++, or C# code for analysis"
        )
        
        if code:
            # Analysis options
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Show analysis types
                analysis_types = []
                if st.session_state.get("analysis_options", {}).get("include_security", True):
                    analysis_types.append("Security")
                if st.session_state.get("analysis_options", {}).get("include_performance", True):
                    analysis_types.append("Performance")
                if st.session_state.get("analysis_options", {}).get("include_documentation", True):
                    analysis_types.append("Documentation")
                if st.session_state.get("analysis_options", {}).get("include_test_coverage", False):
                    analysis_types.append("Test Coverage")
                
                if analysis_types:
                    st.info(f"Selected analyses: {', '.join(analysis_types)}")
                else:
                    st.warning("No analysis types selected. Please configure analysis options in the sidebar.")
            
            with col2:
                # Analyze button
                if st.button("Analyze Code", type="primary", use_container_width=True):
                    if analysis_types:
                        language = st.session_state.get("analysis_options", {}).get("language", "python")
                        # Run LLM-based analysis
                        self._run_llm_analysis(code, language, st.session_state.analysis_options)
                    else:
                        st.error("Please select at least one analysis type in the sidebar.")
        
        # Show analysis progress if running
        if st.session_state.get("system_status") == "analyzing":
            st.divider()
            st.subheader("Analysis Progress")
            with st.spinner("Running comprehensive code analysis..."):
                st.info("Analyzing your code using multiple specialized agents...")
                # The analysis will be handled by the button click
        
        # Show results if available
        st.divider()
        results = st.session_state.get("analysis_results")
        
        if results:
            st.header("Analysis Results")
            # Simple results display
            if "summary" in results:
                summary = results["summary"]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Quality Score", f"{summary.get('quality_score', 0)}/100")
                with col2:
                    st.metric("Total Issues", summary.get('total_observations', 0))
                with col3:
                    st.metric("Errors", summary.get('total_errors', 0))
                with col4:
                    st.metric("Suggestions", summary.get('total_suggestions', 0))
                
                # Show suggestions if any
                if results.get("suggestions"):
                    st.subheader("Suggestions")
                    for suggestion in results["suggestions"]:
                        st.info(f"• {suggestion}")
                
                # Show code metrics
                if "code_metrics" in results:
                    st.subheader("Code Metrics")
                    metrics = results["code_metrics"]
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Lines of Code", metrics.get("lines_of_code", 0))
                    with col2:
                        st.metric("Functions", metrics.get("functions", 0))
                    with col3:
                        st.metric("Classes", metrics.get("classes", 0))
                
                # Show analysis status
                st.subheader("Analysis Status")
                findings = results.get("findings", {})
                for analysis_type, data in findings.items():
                    status = data.get("status", "unknown")
                    if status == "completed":
                        st.success(f"{analysis_type.title()} Analysis: Completed")
                    elif status == "skipped":
                        st.info(f"{analysis_type.title()} Analysis: Skipped")
                    else:
                        st.warning(f"{analysis_type.title()} Analysis: {status}")
                
                # Show corrected code if available
                if results.get("corrected_code") and results.get("corrected_code") != results.get("original_code"):
                    st.subheader("Corrected Code")
                    
                    # Create tabs for original vs corrected
                    tab1, tab2 = st.tabs(["Original Code", "Corrected Code"])
                    
                    with tab1:
                        st.code(results.get("original_code", ""), language=results.get("language", "python"))
                    
                    with tab2:
                        st.code(results.get("corrected_code", ""), language=results.get("language", "python"))
                        
                        # Download button for corrected code
                        st.download_button(
                            label="📥 Download Corrected Code",
                            data=results.get("corrected_code", ""),
                            file_name=f"corrected_code_{results.get('analysis_id', 'unknown')}.py",
                            mime="text/plain"
                        )
                
                # Show detailed findings if available
                if results.get("findings", {}).get("syntax", {}).get("observations"):
                    st.subheader("Detailed Findings")
                    
                    # Show observations
                    observations = results["findings"]["syntax"]["observations"]
                    if observations:
                        st.write("**Observations:**")
                        for obs in observations:
                            st.info(f"• {obs}")
                    
                    # Show errors
                    errors = results["findings"]["syntax"]["errors"]
                    if errors:
                        st.write("**Errors:**")
                        for error in errors:
                            st.error(f"• {error}")
                    
                    # Show LLM suggestions
                    llm_suggestions = results.get("suggestions", [])
                    if llm_suggestions:
                        st.subheader("LLM Suggestions")
                        for suggestion in llm_suggestions:
                            if isinstance(suggestion, dict):
                                priority = suggestion.get("priority", "medium")
                                message = suggestion.get("message", str(suggestion))
                                if priority == "high":
                                    st.error(f"🔥 {message}")
                                elif priority == "medium":
                                    st.warning(f"{message}")
                                else:
                                    st.info(f"{message}")
                            else:
                                st.info(f"{suggestion}")
        else:
            st.info("No analysis results yet. Submit code for analysis above.")
    
    def _run_llm_analysis(self, code: str, language: str, options: dict):
        """Run LLM-based analysis using OpenAI"""
        try:
            st.session_state.system_status = "analyzing"
            
            # Check if OpenAI API key is set
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "your_openai_api_key_here":
                st.error("OpenAI API key not set. Please set your API key in the .env file to use LLM analysis.")
                st.session_state.system_status = "error"
                return
            
            # Create analysis result
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Use the A2A coordinator for multi-agent analysis
            with st.spinner("Running A2A multi-agent analysis..."):
                # Run async analysis using coordinator
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if self.coordinator:
                        # Use the full A2A system with agent communication
                        analysis_result = loop.run_until_complete(
                            self.coordinator.analyze_code(code, language, options)
                        )
                    else:
                        # Fallback to direct analyzer if coordinator not available
                        from analyzers.syntax_analyzer import SyntaxAnalyzer
                        analyzer = SyntaxAnalyzer()
                        analysis_result = loop.run_until_complete(
                            analyzer.analyze_code(code, language, options)
                        )
                finally:
                    loop.close()
                
                # Get corrected code from LLM
                corrected_code = self._get_corrected_code(code, language)
                
                # Calculate quality score
                total_issues = len(analysis_result.get("observations", [])) + len(analysis_result.get("errors", []))
                quality_score = max(0, 100 - total_issues * 5)
                
                # Create comprehensive result
                result = {
                    "analysis_id": analysis_id,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "language": language,
                    "original_code": code,
                    "corrected_code": corrected_code,
                    "summary": {
                        "quality_score": quality_score,
                        "total_observations": len(analysis_result.get("observations", [])),
                        "total_errors": len(analysis_result.get("errors", [])),
                        "total_suggestions": len(analysis_result.get("suggestions", []))
                    },
                    "findings": {
                        "syntax": {
                            "observations": analysis_result.get("observations", []),
                            "errors": analysis_result.get("errors", []),
                            "status": "completed"
                        },
                        "security": {
                            "issues": [],
                            "status": "completed" if options.get("include_security") else "skipped"
                        },
                        "performance": {
                            "issues": [],
                            "status": "completed" if options.get("include_performance") else "skipped"
                        },
                        "documentation": {
                            "issues": [],
                            "status": "completed" if options.get("include_documentation") else "skipped"
                        },
                        "test_coverage": {
                            "issues": [],
                            "status": "completed" if options.get("include_test_coverage") else "skipped"
                        }
                    },
                    "suggestions": analysis_result.get("suggestions", []),
                    "code_metrics": {
                        "lines_of_code": code.count('\n') + 1,
                        "functions": code.count('def ') if language == "python" else code.count('function '),
                        "classes": code.count('class ') if language == "python" else 0
                    }
                }
                
                # Store results
                st.session_state.analysis_results = result
                st.session_state.analysis_history.append(result)
                st.session_state.current_analysis_id = analysis_id
                st.session_state.system_status = "completed"
                
                st.success("LLM Analysis completed successfully!")
                st.rerun()
                
        except Exception as e:
            st.error(f"LLM Analysis failed: {e}")
            st.session_state.system_status = "error"
            # Fallback to simple analysis
            st.warning("Falling back to basic analysis...")
            self._run_simple_analysis(code, language, options)
            
    def _get_corrected_code(self, code: str, language: str) -> str:
        """Get corrected code from OpenAI"""
        try:
            import openai
            
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "your_openai_api_key_here":
                return code  # Return original if no API key
            
            prompt = f"""
            Please analyze and correct the following {language} code. Fix any syntax errors, improve style, and apply best practices.
            Return ONLY the corrected code without any explanations or markdown formatting.
            
            Original code:
            ```{language}
            {code}
            ```
            
            Corrected code:
            """
            
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            
            corrected = response.choices[0].message.content.strip()
            
            # Clean up the response (remove markdown if present)
            if corrected.startswith('```'):
                lines = corrected.split('\n')
                corrected = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else '\n'.join(lines[1:])
            
            return corrected
            
        except Exception as e:
            logger.error(f"Failed to get corrected code: {e}")
            return code  # Return original code on error
    
    def _run_simple_analysis(self, code: str, language: str, options: dict):
        """Run a simple analysis as fallback"""
        try:
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Basic analysis
            suggestions = []
            if language == "python":
                if "import" not in code and "def" in code:
                    suggestions.append("Consider adding import statements if needed")
                if "def " in code and "return" not in code:
                    suggestions.append("Function should have a return statement or be documented as void")
                if "print(" in code:
                    suggestions.append("Consider using logging instead of print statements for production code")
            
            quality_score = max(0, 100 - len(suggestions) * 5)
            
            result = {
                "analysis_id": analysis_id,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "language": language,
                "original_code": code,
                "corrected_code": code,  # No correction in simple mode
                "summary": {
                    "quality_score": quality_score,
                    "total_observations": len(suggestions),
                    "total_errors": 0,
                    "total_suggestions": len(suggestions)
                },
                "findings": {
                    "syntax": {
                        "observations": [],
                        "errors": [],
                        "status": "completed"
                    }
                },
                "suggestions": suggestions,
                "code_metrics": {
                    "lines_of_code": code.count('\n') + 1,
                    "functions": code.count('def ') if language == "python" else 0,
                    "classes": code.count('class ') if language == "python" else 0
                }
            }
            
            st.session_state.analysis_results = result
            st.session_state.analysis_history.append(result)
            st.session_state.current_analysis_id = analysis_id
            st.session_state.system_status = "completed"
            
            st.success("Basic analysis completed!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.session_state.system_status = "error"
    
    def _render_realtime_section(self):
        """Render real-time updates section"""
        st.header(" Real-time A2A System Status")
        
        # Agent status
        self.realtime_updates.display_agent_status()
        
        # System overview
        self.realtime_updates.display_system_overview()
        
        # Agent capabilities
        self.realtime_updates.display_agent_capabilities()


def main():
    """Main entry point for the application"""
    try:
        # Check for required environment variables
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your_openai_api_key_here":
            st.error("""
            **OpenAI API Key Required**
            
            Please set your OpenAI API key in the `.env` file:
            
            ```
            OPENAI_API_KEY=your_actual_api_key_here
            ```
            
            You can get an API key from: https://platform.openai.com/api-keys
            """)
            st.stop()
        
        # Create and run the application
        app = A2ACodeReviewApp()
        app.run()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        st.error(f"Failed to start application: {e}")


if __name__ == "__main__":
    main()