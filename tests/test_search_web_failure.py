
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio

# Add the apps/agent directory to sys.path to import mcp_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestSearchWebFailure(unittest.TestCase):
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy"})
    def setUp(self):
        # Initialize agent with a dummy model name
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    @patch('mcp_agent.DDGS')
    def test_search_web_fallback_on_error(self, mock_ddgs_cls):
        """
        Verify that search_web calls fallback when DDGS fails.
        """
        mock_ddgs_instance = mock_ddgs_cls.return_value
        
        # Simulate DDGS failure
        mock_ddgs_instance.text.side_effect = Exception("DDGS Failed")

        # Mock the fallback method to return success
        self.agent._search_web_manual_fallback = AsyncMock(return_value=[{"title": "Fallback Result", "href": "http://example.com"}])

        # Run async method
        result = asyncio.run(self.agent._execute_search_web({"query": "test query"}))
        
        print("\n--- Fallback Behavior Output ---")
        print(result)
        print("--------------------------------")

        # Verify fallback was called
        self.agent._search_web_manual_fallback.assert_called_once()
        
        # Verify success result from fallback
        self.assertTrue(result.get("success"), "Expected success: true from fallback")
        self.assertEqual(result.get("result")[0]["title"], "Fallback Result")

    @patch('mcp_agent.DDGS')
    def test_search_web_fallback_failure(self, mock_ddgs_cls):
        """
        Verify that search_web returns error if BOTH DDGS and Fallback fail.
        """
        mock_ddgs_instance = mock_ddgs_cls.return_value
        mock_ddgs_instance.text.side_effect = Exception("DDGS Failed")
        
        # Mock fallback to also return empty/fail
        self.agent._search_web_manual_fallback = AsyncMock(return_value=[])

        result = asyncio.run(self.agent._execute_search_web({"query": "test query"}))
        
        print("\n--- Total Failure Output ---")
        print(result)
        print("----------------------------")

        self.assertTrue(result.get("error"), "Expected error: true when both fail")
        self.assertEqual(result.get("error_type"), "SEARCH_FAILED")

if __name__ == '__main__':
    unittest.main()
