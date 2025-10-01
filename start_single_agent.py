"""
Single Agent Startup Script

This script starts a single agent server for testing and development.
Usage: python start_single_agent.py <agent_type> [port]
"""

import asyncio
import sys
import os
from utils.logger import setup_system_logging, get_logger

# Setup logging
setup_system_logging("INFO")
logger = get_logger(__name__)


async def start_agent(agent_type: str, port: int):
    """
    Start a single agent server
    
    Args:
        agent_type: Type of agent to start (syntax, security, performance, documentation, test_coverage)
        port: Port for the agent server
    """
    try:
        # Import the appropriate agent class
        agent_classes = {
            "syntax": ("agents.remote.syntax_agent", "SyntaxAgent"),
            "security": ("agents.remote.security_agent", "SecurityAgent"),
            "performance": ("agents.remote.performance_agent", "PerformanceAgent"),
            "documentation": ("agents.remote.documentation_agent", "DocumentationAgent"),
            "test_coverage": ("agents.remote.test_coverage_agent", "TestCoverageAgent")
        }
        
        if agent_type not in agent_classes:
            print(f" Unknown agent type: {agent_type}")
            print(f"Available types: {', '.join(agent_classes.keys())}")
            sys.exit(1)
        
        module_path, class_name = agent_classes[agent_type]
        module = __import__(module_path, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        
        # Create agent instance
        agent = agent_class(port=port)
        
        # Create and start server
        from agents.remote.agent_server import AgentServer
        server = AgentServer(agent, port)
        
        print(f"Starting {agent.name} on port {port}")
        print(f"Endpoint: http://localhost:{port}")
        print(f"Health: http://localhost:{port}/health")
        print(f"Capabilities: http://localhost:{port}/capabilities")
        print(f"Events: http://localhost:{port}/events")
        print("Press Ctrl+C to stop")
        
        await server.start()
        
    except KeyboardInterrupt:
        print(f"\nStopping {agent_type} agent...")
        logger.info(f"Agent {agent_type} stopped by user")
    except Exception as e:
        logger.error(f"Failed to start {agent_type} agent: {e}")
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python start_single_agent.py <agent_type> [port]")
        print("Available agent types:")
        print("  - syntax (default port: 5001)")
        print("  - security (default port: 5002)")
        print("  - performance (default port: 5003)")
        print("  - documentation (default port: 5004)")
        print("  - test_coverage (default port: 5005)")
        sys.exit(1)
    
    agent_type = sys.argv[1]
    
    # Default ports
    default_ports = {
        "syntax": 5001,
        "security": 5002,
        "performance": 5003,
        "documentation": 5004,
        "test_coverage": 5005
    }
    
    port = int(sys.argv[2]) if len(sys.argv) > 2 else default_ports.get(agent_type, 5001)
    
    # Start the agent
    asyncio.run(start_agent(agent_type, port))


if __name__ == "__main__":
    main()
