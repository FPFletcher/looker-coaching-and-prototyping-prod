
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add agent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestAgentSearch(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_API_KEY"] = "dummy"
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    def test_search_web(self):
        """Test search_web with a real query"""
        print("\nTesting search_web for 'Looker API'...")
        result = asyncio.run(self.agent._execute_search_web({"query": "Looker API documentation"}))
        print(f"Search Result Keys: {result.keys()}")
        if result.get("success"):
             print(f"Top Result: {result['result'][0] if result['result'] else 'None'}")
        else:
             print(f"Search Failed: {result}")
        
        self.assertTrue(result.get("success"))
        self.assertTrue(len(result.get("result", [])) > 0)

    def test_deep_search(self):
        """Test deep_search with a real query"""
        print("\nTesting deep_search for 'Looker API'...")
        # Deep search does search + read. 
        # warning: failure here might be due to anti-bot on specific result pages.
        result = asyncio.run(self.agent._execute_deep_search({"query": "Looker API", "max_results": 1}))
        print(f"Deep Search Result Keys: {result.keys()}")
        
        if result.get("success"):
             results = result.get("results", [])
             print(f"Result count: {len(results)}")
             if results:
                 print(f"First result content length: {len(results[0].get('content', ''))}")
        else:
             print(f"Deep Search Failed: {result}")

        self.assertTrue(result.get("success"))

if __name__ == '__main__':
    unittest.main()
