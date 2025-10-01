#!/usr/bin/env python3
"""
A2A Code Review System - Demo Runner

This script demonstrates how to run the A2A Code Review System
with a simple example analysis.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from registry.agent_registry import AgentRegistry
from agents.coordinator.coordinator import CoordinatorAgent
from agents.remote.syntax_agent import SyntaxAgent
from utils.logger import setup_system_logging


async def run_demo():
    """Run a demonstration of the A2A Code Review System"""
    
    # Setup logging
    setup_system_logging("INFO")
    print("Starting A2A Code Review System Demo")
    
    # Sample code for analysis
    sample_code = '''
def calculate_fibonacci(n):
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

class LongClass:
    """This class is intentionally long to demonstrate code analysis."""
    
    def __init__(self):
        self.data = []
        self.count = 0
        self.name = "LongClass"
        self.description = "A class with many attributes"
        self.version = "1.0.0"
        self.created_at = "2024-01-01"
        self.updated_at = "2024-01-01"
        self.status = "active"
        self.type = "demo"
        self.category = "example"
    
    def method1(self):
        # This method is intentionally long
        result = []
        for i in range(100):
            for j in range(100):
                for k in range(100):
                    result.append(i * j * k)
        return result
    
    def method2(self, arg1, arg2, arg3, arg4, arg5, arg6):
        # Method with too many arguments
        return arg1 + arg2 + arg3 + arg4 + arg5 + arg6
'''
    
    try:
        print("Initializing components...")
        
        # Initialize registry
        registry = AgentRegistry("registry/registry_config.json")
        print(f"Registry initialized with {len(registry.agents)} agents")
        
        # Initialize coordinator
        coordinator = CoordinatorAgent(registry)
        await coordinator.start()
        print("Coordinator agent started")
        
        # Initialize syntax agent (for demonstration)
        syntax_agent = SyntaxAgent(port=5001)
        print("Syntax agent initialized")
        
        # Register syntax agent with registry (in a real system, this would be done automatically)
        agent_info = syntax_agent.get_agent_info()
        registry.register_agent(agent_info)
        print("Syntax agent registered with registry")
        
        print("\nRunning code analysis...")
        
        # Perform analysis
        results = await coordinator.analyze_code(
            code=sample_code,
            language="python",
            options={
                "include_security": True,
                "include_performance": True,
                "include_documentation": True,
                "include_test_coverage": False
            }
        )
        
        print("\nAnalysis Results:")
        print("=" * 50)
        
        # Display summary
        summary = results.get("summary", {})
        print(f"Quality Score: {summary.get('quality_score', 0)}/100")
        print(f"Total Observations: {summary.get('total_observations', 0)}")
        print(f"Total Errors: {summary.get('total_errors', 0)}")
        print(f"Total Suggestions: {summary.get('total_suggestions', 0)}")
        
        # Display observations
        observations = results.get("observations", [])
        if observations:
            print(f"\nObservations ({len(observations)}):")
            for i, obs in enumerate(observations[:5], 1):  # Show first 5
                print(f"  {i}. {obs.get('message', 'No message')}")
                if obs.get('line_number'):
                    print(f"     Line: {obs['line_number']}")
                print(f"     Severity: {obs.get('severity', 'info')}")
        
        # Display errors
        errors = results.get("errors", [])
        if errors:
            print(f"\nErrors ({len(errors)}):")
            for i, error in enumerate(errors[:5], 1):  # Show first 5
                print(f"  {i}. {error.get('message', 'No message')}")
                if error.get('line_number'):
                    print(f"     Line: {error['line_number']}")
                print(f"     Type: {error.get('type', 'unknown')}")
        
        # Display suggestions
        suggestions = results.get("suggestions", [])
        if suggestions:
            print(f"\nSuggestions ({len(suggestions)}):")
            for i, suggestion in enumerate(suggestions[:5], 1):  # Show first 5
                print(f"  {i}. {suggestion.get('message', 'No message')}")
                print(f"     Priority: {suggestion.get('priority', 'medium')}")
        
        # Display recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\nRecommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec.get('message', 'No message')}")
                print(f"     Action: {rec.get('action', 'No specific action')}")
                print(f"     Priority: {rec.get('priority', 'medium')}")
        
        # Display quality scores
        quality_scores = results.get("quality_scores", {})
        if quality_scores:
            print(f"\nQuality Scores:")
            for category, score in quality_scores.items():
                if isinstance(score, (int, float)):
                    print(f"  {category.title()}: {score}/100")
        
        print("\nDemo completed successfully!")
        
        # Cleanup
        await coordinator.stop()
        print("Cleanup completed")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


def main():
    """Main entry point"""
    print("A2A Code Review System - Demo")
    print("=" * 40)
    
    # Check for required environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "your_openai_api_key_here":
        print("Warning: OPENAI_API_KEY not set or is placeholder value")
        print("   The system will work with basic analysis but LLM features will be disabled")
        print("   Set OPENAI_API_KEY in your environment for full functionality")
        print()
    
    # Run the demo
    exit_code = asyncio.run(run_demo())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
