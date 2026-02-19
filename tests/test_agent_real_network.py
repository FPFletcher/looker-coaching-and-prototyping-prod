
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add agent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestAgentRealNetwork(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_API_KEY"] = "dummy"
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    def test_real_read_url(self):
        """Test read_url_content with a real URL"""
        print("\nTesting read_url_content with https://example.com...")
        result = asyncio.run(self.agent._execute_read_url_content({"url": "https://example.com"}))
        print(f"Result: {result}")
        
        self.assertTrue(result.get("success"))
        self.assertIn("Example Domain", result.get("content", ""))

    def test_check_connection(self):
        """Test check_internet_connection"""
        print("\nTesting check_internet_connection...")
        result = asyncio.run(self.agent._execute_check_internet_connection({}))
        print(f"Result: {result}")
        
        self.assertTrue(result.get("success"))

if __name__ == '__main__':
    unittest.main()
