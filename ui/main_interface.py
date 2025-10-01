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
            # Main code input section
            st.header("Code Analysis")
            
            # Get analysis options from session state
            options = st.session_state.get("analysis_options", {})
            
            # Render code input component
            code = self.code_input.render()
            
            if code:
                # Analysis configuration
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Show selected analysis types
                    selected_types = []
                    if options.get("include_security", True):
                        selected_types.append("Security")
                    if options.get("include_performance", True):
                        selected_types.append("Performance")
                    if options.get("include_documentation", True):
                        selected_types.append("Documentation")
                    if options.get("include_test_coverage", False):
                        selected_types.append("Test Coverage")
                    
                    if selected_types:
                        st.info(f"Selected analyses: {', '.join(selected_types)}")
                    else:
                        st.warning("No analysis types selected. Please configure analysis options in the sidebar.")
                
                with col2:
                    # Analyze button
                    if st.button("Analyze Code", type="primary", use_container_width=True):
                        if selected_types:
                            language = options.get("language", "python")
                            self._run_analysis(code, language, options)
                        else:
                            st.error("Please select at least one analysis type in the sidebar.")
            
            # Show analysis progress if running
            if st.session_state.get("system_status") == "analyzing":
                st.divider()
                st.subheader("Analysis Progress")
                with st.spinner("Running comprehensive code analysis..."):
                    st.info("Analyzing your code using multiple specialized agents...")
            
            # Show results if available
            st.divider()
            results = st.session_state.get("analysis_results")
            
            if results:
                st.header("Analysis Results")
                self.results_display.render(results)
            else:
                st.info("Submit code above to see analysis results here.")
                
        except Exception as e:
            self.logger.error(f"Error rendering main interface: {e}")
            st.error(f"Interface error: {e}")
    
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
                
                # Rerun to show results
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