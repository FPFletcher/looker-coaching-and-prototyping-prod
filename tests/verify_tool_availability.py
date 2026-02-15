
import unittest
import sys
import os
import json
import asyncio
from unittest.mock import MagicMock, patch

# Add apps/agent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/agent")))

try:
    from mcp_agent import MCPAgent
except ImportError:
    # Handle case where imports might fail in this environment if paths aren't perfect
    sys.path.append(os.path.abspath("apps/agent"))
    from mcp_agent import MCPAgent

class TestToolAvailability(unittest.TestCase):
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key", "ANTHROPIC_API_KEY": "test_key", "LOOKERSDK_BASE_URL": "url", "LOOKERSDK_CLIENT_ID": "id", "LOOKERSDK_CLIENT_SECRET": "secret"})
    def setUp(self):
        self.agent = MCPAgent(model_name="gemini-2.0-flash")
        
        # Define a list of mock tools including both core and specialized tools
        self.mock_tools = [
            {"name": "get_models", "description": "Get LookML models"},
            {"name": "get_explores", "description": "Get LookML explores"},
            {"name": "run_query", "description": "Run a query"},
            {"name": "get_measures", "description": "Get LookML measures"}, # Simulated binary tool
            {"name": "create_dashboard", "description": "Create a dashboard"},
            {"name": "manage_users", "description": "Manage users"},
            {"name": "dev_mode", "description": "Toggle dev mode"}
        ]

    def test_always_available_tools(self):
        """
        Verify that core analytical tools are returned even if the LLM (mocked) selects nothing.
        """
        query = "show me the top products"
        
        # Mock the LLM response to return EMPTY list (simulating aggressive filtering)
        with patch("google.generativeai.GenerativeModel.generate_content") as mock_generate:
            mock_response = MagicMock()
            mock_response.text = "[]" # LLM says "I need nothing"
            mock_generate.return_value = mock_response
            
            # Run the selection logic
            selected_tools = asyncio.run(self.agent._select_relevant_tools(query, self.mock_tools))
            selected_names = [t["name"] for t in selected_tools]
            
            print(f"Query: {query}")
            print(f"LLM Selected: []")
            print(f"Resulting Tools: {selected_names}")
            
            # Assertions
            self.assertIn("get_models", selected_names)
            self.assertIn("get_explores", selected_names)
            self.assertIn("run_query", selected_names)
            self.assertIn("get_measures", selected_names)
            
            # Specialized tools should NOT be there if LLM didn't pick them
            self.assertNotIn("create_dashboard", selected_names)
            self.assertNotIn("manage_users", selected_names)
            
            print("✅ Core tools were preserved despite empty LLM selection.")

    def test_llm_adds_specialized_tools(self):
        """
        Verify that if LLM selects a specialized tool, it is ADDED to the core tools.
        """
        query = "create a new dashboard for sales"
        
        with patch("google.generativeai.GenerativeModel.generate_content") as mock_generate:
            mock_response = MagicMock()
            mock_response.text = '["create_dashboard"]'
            mock_generate.return_value = mock_response
            
            selected_tools = asyncio.run(self.agent._select_relevant_tools(query, self.mock_tools))
            selected_names = [t["name"] for t in selected_tools]
            
            print(f"\nQuery: {query}")
            print(f"LLM Selected: ['create_dashboard']")
            print(f"Resulting Tools: {selected_names}")
            
            # Assertions
            self.assertIn("create_dashboard", selected_names) # Selected by LLM
            self.assertIn("get_models", selected_names)       # Preserved Core
            self.assertIn("run_query", selected_names)        # Preserved Core
            
            print("✅ Specialized tool added + Core tools preserved.")

if __name__ == '__main__':
    unittest.main()
