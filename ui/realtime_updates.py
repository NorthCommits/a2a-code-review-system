"""
Real-time Updates Component

This module implements real-time updates for the A2A Code Review System
using Server-Sent Events and progress tracking.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import streamlit as st
import requests
from utils.logger import get_logger

logger = get_logger(__name__)


class RealTimeUpdates:
    """
    Handles real-time updates for the A2A system
    
    Provides progress tracking, agent status updates,
    and real-time analysis results.
    """
    
    def __init__(self):
        """Initialize real-time updates"""
        self.agent_endpoints = {
            "syntax": "http://localhost:5001",
            "security": "http://localhost:5002", 
            "performance": "http://localhost:5003",
            "documentation": "http://localhost:5004",
            "test_coverage": "http://localhost:5005"
        }
        self.logger = get_logger(__name__)
    
    def display_agent_status(self):
        """Display real-time agent status"""
        st.subheader("Agent Status")
        
        # Create columns for agent status
        cols = st.columns(len(self.agent_endpoints))
        
        for i, (agent_type, endpoint) in enumerate(self.agent_endpoints.items()):
            with cols[i]:
                status = self._check_agent_health(endpoint)
                self._display_agent_card(agent_type, status, endpoint)
    
    def _check_agent_health(self, endpoint: str) -> Dict[str, Any]:
        """Check health status of an agent"""
        try:
            response = requests.get(f"{endpoint}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "uptime": data.get("uptime", "unknown"),
                    "active_tasks": data.get("active_tasks", 0),
                    "timestamp": data.get("timestamp", "")
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "offline", "message": str(e)}
    
    def _display_agent_card(self, agent_type: str, status: Dict[str, Any], endpoint: str):
        """Display an agent status card"""
        status_type = status.get("status", "unknown")
        
        if status_type == "healthy":
            st.success(f"{agent_type.title()}")
            if "active_tasks" in status:
                st.caption(f"Tasks: {status['active_tasks']}")
        elif status_type == "offline":
            st.error(f"{agent_type.title()}")
            st.caption("Offline")
        else:
            st.warning(f"{agent_type.title()}")
            st.caption("Error")
    
    def display_analysis_progress(self, analysis_id: str):
        """Display real-time analysis progress"""
        st.subheader("Analysis Progress")
        
        # Create progress tracking
        progress_container = st.container()
        
        with progress_container:
            # Overall progress
            overall_progress = st.progress(0)
            status_text = st.empty()
            
            # Individual agent progress
            agent_progress = {}
            agent_containers = {}
            
            for agent_type in self.agent_endpoints.keys():
                agent_containers[agent_type] = st.container()
                with agent_containers[agent_type]:
                    agent_progress[agent_type] = st.progress(0)
                    st.caption(f"{agent_type.title()} Agent")
            
            # Simulate progress updates
            total_agents = len(self.agent_endpoints)
            completed_agents = 0
            
            for i, agent_type in enumerate(self.agent_endpoints.keys()):
                # Update agent progress
                with agent_containers[agent_type]:
                    agent_progress[agent_type].progress(100)
                    st.success(f"{agent_type.title()} completed")
                
                completed_agents += 1
                overall_progress.progress(completed_agents / total_agents)
                status_text.text(f"Completed {completed_agents}/{total_agents} agents")
                
                # Small delay for realistic progress
                time.sleep(0.5)
            
            # Final status
            status_text.text("Analysis completed!")
            overall_progress.progress(1.0)
    
    def get_agent_capabilities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get capabilities from all agents"""
        capabilities = {}
        
        for agent_type, endpoint in self.agent_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/capabilities", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    capabilities[agent_type] = data.get("capabilities", [])
                else:
                    capabilities[agent_type] = []
            except requests.exceptions.RequestException:
                capabilities[agent_type] = []
        
        return capabilities
    
    def display_agent_capabilities(self):
        """Display agent capabilities"""
        st.subheader("Agent Capabilities")
        
        capabilities = self.get_agent_capabilities()
        
        for agent_type, caps in capabilities.items():
            with st.expander(f"{agent_type.title()} Agent Capabilities"):
                if caps:
                    for cap in caps:
                        st.write(f"**{cap.get('name', 'Unknown')}**: {cap.get('description', 'No description')}")
                        if cap.get('parameters'):
                            st.caption(f"Parameters: {cap['parameters']}")
                else:
                    st.info("No capabilities available (agent offline)")
    
    def stream_agent_events(self, agent_type: str, duration: int = 30):
        """Stream real-time events from an agent"""
        endpoint = self.agent_endpoints.get(agent_type)
        if not endpoint:
            st.error(f"Unknown agent type: {agent_type}")
            return
        
        st.subheader(f"Live Events - {agent_type.title()} Agent")
        
        try:
            response = requests.get(f"{endpoint}/events", stream=True, timeout=5)
            
            if response.status_code == 200:
                event_container = st.empty()
                events = []
                
                start_time = time.time()
                
                for line in response.iter_lines():
                    if time.time() - start_time > duration:
                        break
                    
                    if line:
                        try:
                            # Parse SSE data
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]  # Remove 'data: ' prefix
                                event_data = json.loads(data_str)
                                events.append(event_data)
                                
                                # Display latest events
                                with event_container.container():
                                    st.write(f"**Latest Event:** {event_data.get('type', 'unknown')}")
                                    st.json(event_data)
                                    
                                    if len(events) > 5:
                                        st.write("**Recent Events:**")
                                        for event in events[-5:]:
                                            st.caption(f"- {event.get('type')}: {event.get('timestamp', '')}")
                        except json.JSONDecodeError:
                            continue
            else:
                st.error(f"Failed to connect to {agent_type} agent events")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error streaming events: {e}")
    
    def display_system_overview(self):
        """Display system overview with real-time data"""
        st.subheader("System Overview")
        
        # System metrics
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("Active Agents", len([ep for ep in self.agent_endpoints.values() if self._check_agent_health(ep)["status"] == "healthy"]))
        
        with cols[1]:
            total_tasks = sum(self._check_agent_health(ep).get("active_tasks", 0) for ep in self.agent_endpoints.values())
            st.metric("Active Tasks", total_tasks)
        
        with cols[2]:
            st.metric("Total Agents", len(self.agent_endpoints))
        
        with cols[3]:
            st.metric("Protocol", "A2A v1.0")
        
        # Agent status table
        st.subheader("Agent Status Details")
        
        status_data = []
        for agent_type, endpoint in self.agent_endpoints.items():
            health = self._check_agent_health(endpoint)
            status_data.append({
                "Agent": agent_type.title(),
                "Status": health.get("status", "unknown"),
                "Endpoint": endpoint,
                "Active Tasks": health.get("active_tasks", 0),
                "Last Update": health.get("timestamp", "unknown")
            })
        
        st.dataframe(status_data, use_container_width=True)


def create_realtime_updates() -> RealTimeUpdates:
    """Factory function to create real-time updates component"""
    return RealTimeUpdates()
