
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch
import requests

# Add agent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestSearchFailures(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_API_KEY"] = "dummy"
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    def test_read_url_timeout(self):
        """Test read_url_content with a timeout"""
        # Mock requests.get to raise Timeout
        with patch('requests.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
            result = asyncio.run(self.agent._execute_read_url_content({"url": "http://example.com"}))
            
            print(f"\nTimeout Result: {result}")
            self.assertTrue(result.get("error"))
            self.assertEqual(result.get("error_code"), "TIMEOUT")
            self.assertIn("timed out", result.get("message", "").lower())
            
    def test_read_url_404(self):
        """Test read_url_content with 404"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        
        with patch('requests.get', return_value=mock_resp):
            result = asyncio.run(self.agent._execute_read_url_content({"url": "http://example.com/404"}))
            
            print(f"\n404 Result: {result}")
            self.assertTrue(result.get("error"))
            self.assertEqual(result.get("error_code"), "HTTP_ERROR")
            self.assertIn("404", result.get("message"))

    def test_deep_search_silent_fail(self):
        """Test deep_search with empty search results"""
        # Mock search_web to return success but empty results
        mock_search_res = {"success": True, "result": []}
        
        with patch.object(self.agent, '_execute_search_web', return_value=mock_search_res):
            result = asyncio.run(self.agent._execute_deep_search({"query": "ghosts"}))
            
            print(f"\nDeep Search Empty Result: {result}")
            self.assertTrue(result.get("error"))
            self.assertEqual(result.get("error_code"), "NO_RESULTS")

if __name__ == '__main__':
    unittest.main()
