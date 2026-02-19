
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio

# Add the apps/agent directory to sys.path to import mcp_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestDeepSearch(unittest.TestCase):
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy"})
    def setUp(self):
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    @patch('requests.get')
    def test_read_url_content(self, mock_get):
        """Test extraction of text from HTML"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is a <b>test</b> regarding <script>ignore this</script> content extraction.</p>
                <a href="#">Link</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = asyncio.run(self.agent._execute_read_url_content({"url": "http://example.com"}))
        
        print("\n--- Read URL Content Output ---")
        print(result)
        
        self.assertTrue(result["success"])
        self.assertIn("Welcome", result["content"])
        self.assertIn("This is a test regarding content extraction.", result["content"])
        self.assertNotIn("ignore this", result["content"]) # Script content should be ignored

    @patch('requests.get') # For read_url_content
    @patch('mcp_agent.MCPAgent._execute_search_web') # Mock internal search call
    def test_deep_search_flow(self, mock_search, mock_get):
        """Test the orchestration of deep search"""
        # Mock Search Result
        mock_search.return_value = {
            "success": True,
            "result": [
                {"title": "Result 1", "href": "http://res1.com", "body": "snippet 1"},
                {"title": "Result 2", "href": "http://res2.com", "body": "snippet 2"}
            ]
        }

        # Mock Page Content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Full content of page.</p></body></html>"
        mock_get.return_value = mock_response

        # Run Deep Search
        result = asyncio.run(self.agent._execute_deep_search({"query": "AI Agents", "max_results": 2}))

        print("\n--- Deep Search Output ---")
        print(result)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 2)
        self.assertIn("Full content of page", result["results"][0]["content"])
        self.assertEqual(result["results"][0]["title"], "Result 1")

if __name__ == '__main__':
    unittest.main()
