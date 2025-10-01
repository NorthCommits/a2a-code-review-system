"""
Agent Server Startup Script

This script starts multiple agent servers for the A2A Code Review System.
Each agent runs as a separate HTTP server to enable agent-to-agent communication.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from multiprocessing import Process
import uvicorn
from utils.logger import setup_system_logging, get_logger

# Setup logging
setup_system_logging("INFO")
logger = get_logger(__name__)


class AgentManager:
    """
    Manages multiple agent servers
    """
    
    def __init__(self):
        self.processes: List[Process] = []
        self.agent_configs = [
            {
                "name": "syntax-agent",
                "agent_class": "agents.remote.syntax_agent.SyntaxAgent",
                "port": 5001,
                "description": "Syntax Analysis Agent"
            },
            {
                "name": "security-agent", 
                "agent_class": "agents.remote.security_agent.SecurityAgent",
                "port": 5002,
                "description": "Security Scanner Agent"
            },
            {
                "name": "performance-agent",
                "agent_class": "agents.remote.performance_agent.PerformanceAgent", 
                "port": 5003,
                "description": "Performance Analyzer Agent"
            },
            {
                "name": "documentation-agent",
                "agent_class": "agents.remote.documentation_agent.DocumentationAgent",
                "port": 5004,
                "description": "Documentation Quality Agent"
            },
            {
                "name": "test-coverage-agent",
                "agent_class": "agents.remote.test_coverage_agent.TestCoverageAgent",
                "port": 5005,
                "description": "Test Coverage Agent"
            }
        ]
    
    def start_agent_server(self, config: Dict[str, Any]):
        """
        Start a single agent server in a separate process
        
        Args:
            config: Agent configuration
        """
        try:
            logger.info(f"Starting {config['description']} on port {config['port']}")
            
            # Import the agent class
            module_path, class_name = config['agent_class'].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Create agent instance
            agent = agent_class(port=config['port'])
            
            # Start the agent server
            from agents.remote.agent_server import AgentServer
            server = AgentServer(agent, config['port'])
            
            # Run the server
            asyncio.run(server.start())
            
        except Exception as e:
            logger.error(f"Failed to start {config['name']}: {e}")
            sys.exit(1)
    
    def start_all_agents(self):
        """Start all agent servers"""
        logger.info("Starting all A2A agent servers...")
        
        for config in self.agent_configs:
            try:
                # Create process for each agent
                process = Process(
                    target=self.start_agent_server,
                    args=(config,),
                    name=f"agent-{config['name']}"
                )
                process.start()
                self.processes.append(process)
                
                logger.info(f"Started {config['description']} (PID: {process.pid})")
                
                # Small delay between starting agents
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to start {config['name']}: {e}")
        
        logger.info(f"Started {len(self.processes)} agent servers")
        
        # Print agent endpoints
        print("\n" + "="*60)
        print("A2A AGENT SERVERS STARTED")
        print("="*60)
        print("Agent Endpoints:")
        for config in self.agent_configs:
            print(f"  {config['description']}: http://localhost:{config['port']}")
        print("\nHealth Check Endpoints:")
        for config in self.agent_configs:
            print(f"  {config['description']}: http://localhost:{config['port']}/health")
        print("\nSSE Event Streams:")
        for config in self.agent_configs:
            print(f"  {config['description']}: http://localhost:{config['port']}/events")
        print("="*60)
        print("All agents are ready for A2A communication!")
        print("="*60 + "\n")
    
    def stop_all_agents(self):
        """Stop all agent servers"""
        logger.info("Stopping all agent servers...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.join(timeout=5)
                
                if process.is_alive():
                    logger.warning(f"Force killing process {process.pid}")
                    process.kill()
                    process.join()
                    
                logger.info(f"Stopped agent process {process.pid}")
                
            except Exception as e:
                logger.error(f"Error stopping process {process.pid}: {e}")
        
        self.processes.clear()
        logger.info("All agent servers stopped")


def main():
    """Main function to start agent servers"""
    manager = AgentManager()
    
    try:
        # Start all agents
        manager.start_all_agents()
        
        # Keep the main process alive
        print("\nPress Ctrl+C to stop all agents...")
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping all agents...")
        manager.stop_all_agents()
        print("All agents stopped successfully!")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        manager.stop_all_agents()
        sys.exit(1)


if __name__ == "__main__":
    main()
