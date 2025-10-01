"""
UI Components

This module implements reusable Streamlit UI components for the A2A Code Review System.
"""

import streamlit as st
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class CodeInputComponent:
    """
    Code input component for the A2A Code Review System
    
    Provides a text area for code input with syntax highlighting
    and language selection.
    """
    
    def __init__(self):
        """Initialize code input component"""
        self.logger = get_logger(__name__)
    
    def render(self) -> Optional[str]:
        """
        Render the code input component
        
        Returns:
            Code string if provided, None otherwise
        """
        try:
            # Code input area
            st.subheader("Enter Code for Analysis")
            
            # Sample code option
            if st.checkbox("Load sample code"):
                sample_code = self._get_sample_code()
                code = st.text_area(
                    "Code",
                    value=sample_code,
                    height=400,
                    placeholder="Paste your code here...",
                    help="Enter the code you want to analyze"
                )
            else:
                code = st.text_area(
                    "Code",
                    height=400,
                    placeholder="Paste your code here...",
                    help="Enter the code you want to analyze"
                )
            
            # Code statistics
            if code:
                self._display_code_stats(code)
            
            return code if code.strip() else None
            
        except Exception as e:
            self.logger.error(f"Error rendering code input: {e}")
            st.error(f"Code input error: {e}")
            return None
    
    def _get_sample_code(self) -> str:
        """Get sample code for demonstration"""
        return '''def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def process_user_input(user_input):
    # Potential SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return query

def inefficient_sort(data):
    # Inefficient bubble sort implementation
    for i in range(len(data)):
        for j in range(len(data) - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
'''
    
    def _display_code_stats(self, code: str):
        """Display code statistics"""
        lines = code.split('\n')
        total_lines = len(lines)
        non_empty_lines = len([line for line in lines if line.strip()])
        total_chars = len(code)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Lines", total_lines)
        with col2:
            st.metric("Non-empty Lines", non_empty_lines)
        with col3:
            st.metric("Characters", total_chars)


class ResultsDisplayComponent:
    """
    Results display component for the A2A Code Review System
    
    Displays analysis results in a structured and user-friendly format.
    """
    
    def __init__(self):
        """Initialize results display component"""
        self.logger = get_logger(__name__)
    
    def render(self, results: Dict[str, Any]):
        """
        Render the results display component
        
        Args:
            results: Analysis results dictionary
        """
        try:
            # Results header
            analysis_id = results.get("analysis_id", "unknown")
            timestamp = results.get("timestamp", "")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"Analysis Results: {analysis_id}")
            with col2:
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        st.caption(f"Completed: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    except:
                        st.caption(f"Completed: {timestamp}")
            
            # Summary metrics
            self._render_summary(results)
            
            # Detailed results
            self._render_detailed_results(results)
            
            # Corrected code
            self._render_corrected_code(results)
            
            # Download options
            self._render_download_options(results)
            
        except Exception as e:
            self.logger.error(f"Error rendering results: {e}")
            st.error(f"Results display error: {e}")
    
    def _render_summary(self, results: Dict[str, Any]):
        """Render results summary"""
        summary = results.get("summary", {})
        
        if summary:
            st.subheader("📊 Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Quality Score",
                    f"{summary.get('quality_score', 0)}/100",
                    delta=f"{summary.get('quality_score', 0) - 50}" if summary.get('quality_score', 0) > 50 else None
                )
            
            with col2:
                st.metric("Observations", summary.get("total_observations", 0))
            
            with col3:
                st.metric("Errors", summary.get("total_errors", 0))
            
            with col4:
                st.metric("Suggestions", summary.get("total_suggestions", 0))
            
            # Quality score visualization
            quality_score = summary.get("quality_score", 0)
            if quality_score >= 80:
                st.success(f"🎉 Excellent code quality! Score: {quality_score}/100")
            elif quality_score >= 60:
                st.info(f"👍 Good code quality. Score: {quality_score}/100")
            elif quality_score >= 40:
                st.warning(f"⚠️ Code quality needs improvement. Score: {quality_score}/100")
            else:
                st.error(f"🚨 Poor code quality. Score: {quality_score}/100")
    
    def _render_detailed_results(self, results: Dict[str, Any]):
        """Render detailed analysis results"""
        # Observations
        observations = results.get("observations", [])
        if observations:
            st.subheader("🔍 Observations")
            for i, obs in enumerate(observations, 1):
                self._render_observation(obs, i)
        
        # Errors
        errors = results.get("errors", [])
        if errors:
            st.subheader("❌ Errors")
            
            # Handle both dict and list formats
            if isinstance(errors, dict):
                critical_errors = errors.get("critical", [])
                non_critical_errors = errors.get("non_critical", [])
                
                if critical_errors:
                    st.error("🚨 Critical Errors")
                    for i, error in enumerate(critical_errors, 1):
                        self._render_error(error, i, "critical")
                
                if non_critical_errors:
                    st.warning("⚠️ Non-Critical Errors")
                    for i, error in enumerate(non_critical_errors, 1):
                        self._render_error(error, i, "warning")
            else:
                # Handle list format
                for i, error in enumerate(errors, 1):
                    severity = error.get("severity", "error")
                    self._render_error(error, i, severity)
        
        # Suggestions
        suggestions = results.get("suggestions", [])
        if suggestions:
            st.subheader("💡 Suggestions")
            for i, suggestion in enumerate(suggestions, 1):
                self._render_suggestion(suggestion, i)
        
        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            st.subheader("📋 Recommendations")
            for i, rec in enumerate(recommendations, 1):
                self._render_recommendation(rec, i)
    
    def _render_observation(self, obs: Dict[str, Any], index: int):
        """Render a single observation"""
        with st.expander(f"Observation {index}: {obs.get('type', 'Unknown')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Message:** {obs.get('message', 'No message')}")
                if obs.get('line_number'):
                    st.write(f"**Line:** {obs['line_number']}")
                if obs.get('suggestion'):
                    st.write(f"**Suggestion:** {obs['suggestion']}")
            
            with col2:
                severity = obs.get('severity', 'info')
                if severity == 'critical':
                    st.error("Critical")
                elif severity == 'warning':
                    st.warning("Warning")
                elif severity == 'info':
                    st.info("Info")
                else:
                    st.write(severity.title())
    
    def _render_error(self, error: Dict[str, Any], index: int, severity: str):
        """Render a single error"""
        with st.expander(f"Error {index}: {error.get('type', 'Unknown')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Message:** {error.get('message', 'No message')}")
                if error.get('line_number'):
                    st.write(f"**Line:** {error['line_number']}")
                if error.get('suggestion'):
                    st.write(f"**Fix:** {error['suggestion']}")
            
            with col2:
                if severity == 'critical':
                    st.error("Critical")
                elif severity == 'warning':
                    st.warning("Warning")
                else:
                    st.error("Error")
    
    def _render_suggestion(self, suggestion: Dict[str, Any], index: int):
        """Render a single suggestion"""
        with st.expander(f"Suggestion {index}: {suggestion.get('type', 'Improvement')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Message:** {suggestion.get('message', 'No message')}")
                if suggestion.get('line_number'):
                    st.write(f"**Line:** {suggestion['line_number']}")
                if suggestion.get('example'):
                    st.code(suggestion['example'], language='python')
            
            with col2:
                priority = suggestion.get('priority', 'medium')
                if priority == 'high':
                    st.error("High Priority")
                elif priority == 'medium':
                    st.warning("Medium Priority")
                else:
                    st.info("Low Priority")
    
    def _render_recommendation(self, rec: Dict[str, Any], index: int):
        """Render a single recommendation"""
        with st.expander(f"Recommendation {index}: {rec.get('type', 'General').title()}"):
            st.write(f"**Message:** {rec.get('message', 'No message')}")
            st.write(f"**Action:** {rec.get('action', 'No specific action')}")
            
            priority = rec.get('priority', 'medium')
            if priority == 'critical':
                st.error("🚨 Critical Priority")
            elif priority == 'high':
                st.error("🔴 High Priority")
            elif priority == 'medium':
                st.warning("🟡 Medium Priority")
            else:
                st.info("🟢 Low Priority")
    
    def _render_corrected_code(self, results: Dict[str, Any]):
        """Render corrected code if available"""
        corrected_code = results.get("corrected_code")
        
        if corrected_code:
            st.subheader("🔧 Corrected Code")
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(corrected_code, language='python')
            
            with col2:
                if st.button("📋 Copy Code"):
                    st.write("Code copied to clipboard!")
    
    def _render_download_options(self, results: Dict[str, Any]):
        """Render download options"""
        st.subheader("📥 Download Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download as JSON
            json_data = json.dumps(results, indent=2)
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name=f"analysis_results_{results.get('analysis_id', 'unknown')}.json",
                mime="application/json"
            )
        
        with col2:
            # Download corrected code
            corrected_code = results.get("corrected_code")
            if corrected_code:
                st.download_button(
                    label="🐍 Download Corrected Code",
                    data=corrected_code,
                    file_name=f"corrected_code_{results.get('analysis_id', 'unknown')}.py",
                    mime="text/plain"
                )
        
        with col3:
            # Download summary report
            summary_text = self._generate_summary_report(results)
            st.download_button(
                label="📋 Download Summary",
                data=summary_text,
                file_name=f"analysis_summary_{results.get('analysis_id', 'unknown')}.txt",
                mime="text/plain"
            )
    
    def _generate_summary_report(self, results: Dict[str, Any]) -> str:
        """Generate a text summary report"""
        analysis_id = results.get("analysis_id", "unknown")
        timestamp = results.get("timestamp", "")
        summary = results.get("summary", {})
        
        report = f"""
A2A Code Review Analysis Report
===============================

Analysis ID: {analysis_id}
Timestamp: {timestamp}

Summary:
--------
Quality Score: {summary.get('quality_score', 0)}/100
Total Observations: {summary.get('total_observations', 0)}
Total Errors: {summary.get('total_errors', 0)}
Total Suggestions: {summary.get('total_suggestions', 0)}

Errors:
-------
"""
        
        errors = results.get("errors", [])
        if isinstance(errors, dict):
            critical_errors = errors.get("critical", [])
            non_critical_errors = errors.get("non_critical", [])
            
            for error in critical_errors:
                report += f"- CRITICAL: {error.get('message', 'No message')}\n"
            
            for error in non_critical_errors:
                report += f"- {error.get('severity', 'error').upper()}: {error.get('message', 'No message')}\n"
        else:
            for error in errors:
                report += f"- {error.get('severity', 'error').upper()}: {error.get('message', 'No message')}\n"
        
        report += "\nSuggestions:\n-----------\n"
        suggestions = results.get("suggestions", [])
        for suggestion in suggestions:
            report += f"- {suggestion.get('message', 'No message')}\n"
        
        return report


class ProgressComponent:
    """
    Progress component for the A2A Code Review System
    
    Displays analysis progress and status updates.
    """
    
    def __init__(self):
        """Initialize progress component"""
        self.logger = get_logger(__name__)
    
    def render(self):
        """Render the progress component"""
        try:
            st.subheader("🔄 Analysis Progress")
            
            # Progress bar
            progress_bar = st.progress(0)
            
            # Status text
            status_text = st.empty()
            
            # Analysis steps
            steps = [
                "Initializing analysis...",
                "Distributing tasks to agents...",
                "Running syntax analysis...",
                "Running security scan...",
                "Running performance analysis...",
                "Running documentation check...",
                "Aggregating results...",
                "Generating report..."
            ]
            
            # Simulate progress (in a real implementation, this would be updated by the actual analysis)
            for i, step in enumerate(steps):
                progress = (i + 1) / len(steps)
                progress_bar.progress(progress)
                status_text.text(step)
                st.empty()  # Add a small delay for visual effect
            
            # Final status
            status_text.text("Analysis complete!")
            
        except Exception as e:
            self.logger.error(f"Error rendering progress: {e}")
            st.error(f"Progress display error: {e}")
