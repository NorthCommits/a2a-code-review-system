"""
A2A System Test Script

This script tests the complete A2A agent communication system
to verify that all components work together properly.
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any, List
from utils.logger import setup_system_logging, get_logger

# Setup logging
setup_system_logging("INFO")
logger = get_logger(__name__)


class A2ASystemTester:
    """
    Tests the complete A2A system functionality
    """
    
    def __init__(self):
        """Initialize the tester"""
        self.agent_endpoints = {
            "syntax": "http://localhost:5001",
            "security": "http://localhost:5002",
            "performance": "http://localhost:5003",
            "documentation": "http://localhost:5004",
            "test_coverage": "http://localhost:5005"
        }
        self.test_results = {}
        self.logger = get_logger(__name__)
    
    def test_agent_health(self) -> Dict[str, bool]:
        """Test agent health endpoints"""
        self.logger.info("Testing agent health endpoints...")
        
        health_results = {}
        
        for agent_type, endpoint in self.agent_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/health", timeout=5)
                if response.status_code == 200:
                    health_results[agent_type] = True
                    self.logger.info(f"{agent_type} agent is healthy")
                else:
                    health_results[agent_type] = False
                    self.logger.error(f"{agent_type} agent health check failed: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                health_results[agent_type] = False
                self.logger.error(f"{agent_type} agent is offline: {e}")
        
        self.test_results["health"] = health_results
        return health_results
    
    def test_agent_capabilities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Test agent capabilities endpoints"""
        self.logger.info("Testing agent capabilities endpoints...")
        
        capabilities_results = {}
        
        for agent_type, endpoint in self.agent_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/capabilities", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    capabilities = data.get("capabilities", [])
                    capabilities_results[agent_type] = capabilities
                    self.logger.info(f"{agent_type} agent capabilities: {len(capabilities)} capabilities")
                else:
                    capabilities_results[agent_type] = []
                    self.logger.error(f"{agent_type} agent capabilities failed: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                capabilities_results[agent_type] = []
                self.logger.error(f"{agent_type} agent capabilities error: {e}")
        
        self.test_results["capabilities"] = capabilities_results
        return capabilities_results
    
    def test_agent_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Test agent analysis endpoints"""
        self.logger.info("Testing agent analysis endpoints...")
        
        test_code = '''
def hello_world():
    print("Hello, World!")
    return "success"

def calculate_sum(a, b):
    result = a + b
    return result
'''
        
        analysis_results = {}
        
        for agent_type, endpoint in self.agent_endpoints.items():
            try:
                # Create A2A task request
                task_request = {
                    "jsonrpc": "2.0",
                    "id": f"test_{agent_type}_{int(time.time())}",
                    "method": "analyze_code",
                    "params": {
                        "code": test_code,
                        "language": "python",
                        "options": {},
                        "task_id": f"test_{agent_type}"
                    }
                }
                
                response = requests.post(
                    f"{endpoint}/analyze",
                    json=task_request,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    analysis_results[agent_type] = {
                        "success": True,
                        "result": data.get("result", {}),
                        "status": data.get("status", "unknown")
                    }
                    self.logger.info(f"{agent_type} agent analysis completed")
                else:
                    analysis_results[agent_type] = {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "response": response.text
                    }
                    self.logger.error(f"{agent_type} agent analysis failed: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                analysis_results[agent_type] = {
                    "success": False,
                    "error": str(e)
                }
                self.logger.error(f"{agent_type} agent analysis error: {e}")
        
        self.test_results["analysis"] = analysis_results
        return analysis_results
    
    def test_coordinator_integration(self) -> Dict[str, Any]:
        """Test coordinator integration with agents"""
        self.logger.info("Testing coordinator integration...")
        
        try:
            # Import coordinator components
            from registry.agent_registry import AgentRegistry
            from agents.coordinator.coordinator import CoordinatorAgent
            
            # Initialize registry
            registry = AgentRegistry("registry/registry_config.json")
            
            # Initialize coordinator
            coordinator = CoordinatorAgent(registry)
            
            # Test coordinator initialization
            init_result = {
                "registry_loaded": len(registry.agents) > 0,
                "coordinator_created": coordinator is not None,
                "agent_count": len(registry.agents)
            }
            
            self.logger.info(f"Coordinator integration: {init_result}")
            
        except Exception as e:
            init_result = {
                "error": str(e),
                "success": False
            }
            self.logger.error(f"Coordinator integration failed: {e}")
        
        self.test_results["coordinator"] = init_result
        return init_result
    
    def test_sse_events(self) -> Dict[str, bool]:
        """Test Server-Sent Events endpoints"""
        self.logger.info("Testing SSE event streams...")
        
        sse_results = {}
        
        for agent_type, endpoint in self.agent_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/events", stream=True, timeout=5)
                if response.status_code == 200:
                    sse_results[agent_type] = True
                    self.logger.info(f"{agent_type} agent SSE stream working")
                else:
                    sse_results[agent_type] = False
                    self.logger.error(f"{agent_type} agent SSE failed: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                sse_results[agent_type] = False
                self.logger.error(f"{agent_type} agent SSE error: {e}")
        
        self.test_results["sse"] = sse_results
        return sse_results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate report"""
        self.logger.info("Starting comprehensive A2A system test...")
        
        print("A2A SYSTEM COMPREHENSIVE TEST")
        print("=" * 50)
        
        # Run all tests
        health_results = self.test_agent_health()
        capabilities_results = self.test_agent_capabilities()
        analysis_results = self.test_agent_analysis()
        coordinator_results = self.test_coordinator_integration()
        sse_results = self.test_sse_events()
        
        # Generate summary
        total_agents = len(self.agent_endpoints)
        healthy_agents = sum(1 for healthy in health_results.values() if healthy)
        working_analysis = sum(1 for result in analysis_results.values() if result.get("success", False))
        working_sse = sum(1 for working in sse_results.values() if working)
        
        summary = {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "working_analysis": working_analysis,
            "working_sse": working_sse,
            "coordinator_working": coordinator_results.get("success", False),
            "overall_score": (healthy_agents + working_analysis + working_sse) / (total_agents * 3) * 100
        }
        
        # Print results
        print(f"\nTEST RESULTS SUMMARY:")
        print(f"  Total Agents: {total_agents}")
        print(f"  Healthy Agents: {healthy_agents}/{total_agents}")
        print(f"  Working Analysis: {working_analysis}/{total_agents}")
        print(f"  Working SSE: {working_sse}/{total_agents}")
        print(f"  Coordinator: {'Working' if coordinator_results.get('success') else 'Failed'}")
        print(f"  Overall Score: {summary['overall_score']:.1f}%")
        
        if summary['overall_score'] >= 80:
            print(f"\nA2A SYSTEM TEST PASSED! ({summary['overall_score']:.1f}%)")
        elif summary['overall_score'] >= 60:
            print(f"\nA2A SYSTEM PARTIALLY WORKING ({summary['overall_score']:.1f}%)")
        else:
            print(f"\nA2A SYSTEM TEST FAILED ({summary['overall_score']:.1f}%)")
        
        print("=" * 50)
        
        return {
            "summary": summary,
            "detailed_results": self.test_results
        }


def main():
    """Main test function"""
    tester = A2ASystemTester()
    
    try:
        results = tester.run_comprehensive_test()
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to test_results.json")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"Test execution failed: {e}")


if __name__ == "__main__":
    main()
