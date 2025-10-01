"""
Main Interface

This module implements the main Streamlit interface for the A2A Code Review System.
Provides the primary user interface for code input and results display.
"""

import streamlit as st
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from .components import CodeInputComponent, ResultsDisplayComponent, ProgressComponent
from agents.coordinator.coordinator import CoordinatorAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class MainInterface:
    """
    Main interface for the A2A Code Review System
    
    Manages the primary user interface including code input,
    analysis execution, and results display.
    """
    
    def __init__(self, coordinator: CoordinatorAgent):
        """
        Initialize main interface
        
        Args:
            coordinator: Coordinator agent instance
        """
        self.coordinator = coordinator
        self.logger = get_logger(__name__)
        
        # Initialize UI components
        self.code_input = CodeInputComponent()
        self.results_display = ResultsDisplayComponent()
        self.progress = ProgressComponent()
        
        self.logger.info("Main interface initialized")
    
    def render(self):
        """Render the main interface"""
        try:
            # Create tabs for different sections
            tab1, tab2, tab3 = st.tabs(["📝 Code Analysis", "📊 Results", "🔧 System"])
            
            with tab1:
                self._render_code_analysis_tab()
            
            with tab2:
                self._render_results_tab()
            
            with tab3:
                self._render_system_tab()
                
        except Exception as e:
            self.logger.error(f"Error rendering main interface: {e}")
            st.error(f"Interface error: {e}")
    
    def _render_code_analysis_tab(self):
        """Render the code analysis tab"""
        st.header("Code Analysis")
        
        # Get analysis options from session state
        options = st.session_state.get("analysis_options", {})
        
        # Render code input component
        code = self.code_input.render()
        
        if code:
            # Analysis options
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Analysis Configuration")
                
                # Language selection
                language = options.get("language", "python")
                
                # Analysis type checkboxes
                analysis_types = {
                    "Syntax & Style": options.get("include_syntax", True),
                    "Security Scan": options.get("include_security", True),
                    "Performance": options.get("include_performance", True),
                    "Documentation": options.get("include_documentation", True),
                    "Test Coverage": options.get("include_test_coverage", False)
                }
                
                # Display selected analysis types
                selected_types = [name for name, selected in analysis_types.items() if selected]
                if selected_types:
                    st.info(f"Selected analyses: {', '.join(selected_types)}")
                else:
                    st.warning("No analysis types selected. Please configure analysis options in the sidebar.")
            
            with col2:
                # Analyze button
                if st.button("🔍 Analyze Code", type="primary", use_container_width=True):
                    if selected_types:
                        self._run_analysis(code, language, options)
                    else:
                        st.error("Please select at least one analysis type in the sidebar.")
            
            # Show current analysis progress
            if st.session_state.system_status == "analyzing":
                self.progress.render()
    
    def _render_results_tab(self):
        """Render the results tab"""
        st.header("Analysis Results")
        
        results = st.session_state.get("analysis_results")
        
        if results:
            self.results_display.render(results)
        else:
            st.info("No analysis results yet. Submit code for analysis in the Code Analysis tab.")
    
    def _render_system_tab(self):
        """Render the system information tab"""
        st.header("System Information")
        
        # Agent status
        st.subheader("Agent Status")
        try:
            status_info = asyncio.run(self._get_agent_status())
            
            if "agents" in status_info and "registry" in status_info["agents"]:
                registry_info = status_info["agents"]["registry"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Agents", registry_info.get("total_agents", 0))
                with col2:
                    st.metric("Active Agents", registry_info.get("active_agents", 0))
                with col3:
                    st.metric("Healthy Agents", registry_info.get("healthy_agents", 0))
                
                # Agent details
                if "agents" in status_info["agents"]:
                    st.subheader("Agent Details")
                    agents_info = status_info["agents"]["agents"]
                    
                    for agent_id, agent_info in agents_info.items():
                        with st.expander(f"Agent: {agent_info.get('name', agent_id)}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Status:** {agent_info.get('status', 'unknown')}")
                                st.write(f"**Health:** {agent_info.get('health_status', 'unknown')}")
                                st.write(f"**Active Tasks:** {agent_info.get('active_tasks', 0)}")
                            
                            with col2:
                                st.write(f"**Total Tasks:** {agent_info.get('total_tasks', 0)}")
                                if agent_info.get('response_time'):
                                    st.write(f"**Response Time:** {agent_info['response_time']:.2f}s")
                                if agent_info.get('last_seen'):
                                    st.write(f"**Last Seen:** {agent_info['last_seen']}")
            else:
                st.warning("No agent information available")
                
        except Exception as e:
            st.error(f"Error getting agent status: {e}")
        
        # System capabilities
        st.subheader("Analysis Capabilities")
        try:
            capabilities = self.coordinator.get_analysis_capabilities()
            
            for analysis_type, config in capabilities.items():
                with st.expander(f"📋 {analysis_type.replace('_', ' ').title()}"):
                    st.write(f"**Capabilities:** {', '.join(config.get('capabilities', []))}")
                    st.write(f"**Priority:** {config.get('priority', 'N/A')}")
                    
        except Exception as e:
            st.error(f"Error getting capabilities: {e}")
        
        # System health
        st.subheader("System Health")
        try:
            health_info = asyncio.run(self.coordinator.health_check())
            
            status = health_info.get("status", "unknown")
            if status == "healthy":
                st.success("🟢 System is healthy")
            elif status == "degraded":
                st.warning("🟡 System is degraded")
            else:
                st.error("🔴 System is unhealthy")
            
            # Show detailed health information
            if "coordinator" in health_info:
                coordinator_health = health_info["coordinator"]
                st.write(f"**Uptime:** {coordinator_health.get('uptime', 0):.1f} seconds")
                st.write(f"**Active Tasks:** {coordinator_health.get('active_tasks', 0)}")
            
        except Exception as e:
            st.error(f"Error getting system health: {e}")
    
    def _run_analysis(self, code: str, language: str, options: Dict[str, Any]):
        """
        Run code analysis
        
        Args:
            code: Code to analyze
            language: Programming language
            options: Analysis options
        """
        try:
            # Update session state
            st.session_state.system_status = "analyzing"
            
            # Prepare analysis options
            analysis_options = {
                "include_security": options.get("include_security", True),
                "include_performance": options.get("include_performance", True),
                "include_documentation": options.get("include_documentation", True),
                "include_test_coverage": options.get("include_test_coverage", False)
            }
            
            # Run analysis asynchronously
            with st.spinner("Running comprehensive code analysis..."):
                results = asyncio.run(self.coordinator.analyze_code(code, language, analysis_options))
                
                # Store results
                st.session_state.analysis_results = results
                st.session_state.system_status = "completed"
                
                # Show success message
                st.success("Analysis completed successfully!")
                
                # Switch to results tab
                st.rerun()
                
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            st.error(f"Analysis failed: {e}")
            st.session_state.system_status = "error"
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get agent status information"""
        try:
            return await self.coordinator.get_agent_status()
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return {"error": str(e)}
