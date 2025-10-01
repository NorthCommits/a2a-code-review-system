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
from utils.logger import setup_system_logging, get_logger
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
                page_icon="🔍",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            
            # Main title and description
            st.title("🔍 A2A Code Review System")
            st.markdown("""
            **Multi-Agent Code Quality Analysis System**
            
            This system uses multiple specialized AI agents to analyze your code for:
            - **Syntax & Style** - Code formatting and linting
            - **Security** - Vulnerability detection and security best practices
            - **Performance** - Performance optimization opportunities
            - **Documentation** - Code documentation quality
            - **Test Coverage** - Test completeness and quality
            """)
            
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
            
            # Create main interface
            if self.interface:
                self.interface.render()
            
            # Sidebar with system information
            self._render_sidebar()
            
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
                st.success("🟢 System Ready")
            elif status == "analyzing":
                st.info("🟡 Analyzing...")
            elif status == "completed":
                st.success("🟢 Analysis Complete")
            elif status == "error":
                st.error("🔴 System Error")
            else:
                st.warning("🟡 Initializing...")
            
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
                            
                            status_icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
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
                index=0
            )
            
            # Analysis options
            st.subheader("Analysis Options")
            include_security = st.checkbox("Security Analysis", value=True)
            include_performance = st.checkbox("Performance Analysis", value=True)
            include_documentation = st.checkbox("Documentation Check", value=True)
            include_test_coverage = st.checkbox("Test Coverage", value=False)
            
            # Store options in session
            st.session_state.analysis_options = {
                "language": language,
                "include_security": include_security,
                "include_performance": include_performance,
                "include_documentation": include_documentation,
                "include_test_coverage": include_test_coverage
            }
            
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
