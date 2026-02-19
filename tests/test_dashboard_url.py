
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add agent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from mcp_agent import MCPAgent

class TestDashboardURL(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_API_KEY"] = "dummy"
        self.agent = MCPAgent(model_name="gemini-2.0-flash")

    def test_create_dashboard_returns_full_url(self):
        """Test that create_dashboard returns full_url with /embed/"""
        # Mock SDK
        mock_sdk = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard.id = "999"
        mock_dashboard.title = "Test Dash"
        mock_sdk.create_dashboard.return_value = mock_dashboard
        mock_sdk.me.return_value.personal_folder_id = "100"
        
        # Test helper method directly
        with patch.object(self.agent, '_init_sdk', return_value=mock_sdk):
            args = {"title": "Test Dash"}
            result = self.agent._execute_create_dashboard(
                args, 
                url="https://test.looker.com:19999", 
                client_id="cid", 
                client_secret="cs"
            )
            
            print(f"Result: {result}")
            
            self.assertTrue(result["success"])
            res_data = result["result"]
            
            self.assertIn("full_url", res_data)
            self.assertEqual(res_data["full_url"], "https://test.looker.com:19999/embed/dashboards/999")
            self.assertIn("LOCKED URL", res_data["message"])

if __name__ == '__main__':
    unittest.main()
