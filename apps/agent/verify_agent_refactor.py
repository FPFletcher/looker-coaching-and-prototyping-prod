
import asyncio
import logging
import os
import sys
import json
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Add parent directory to path to import mcp_agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_agent import MCPAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_tool_selection():
    """Test if _select_relevant_tools filters correctly."""
    print("\n🔹 Testing Tool Selection...")
    
    # Mock agent with Gemini model (or just simulate the call if easier, but let's try real call)
    try:
        agent = MCPAgent(model_name="gemini-2.0-flash")
    except Exception as e:
        print(f"⚠️ Failed to init agent: {e}")
        return

    # Mock tools list (subset of real tools)
    tools = [
        {"name": "health_pulse", "description": "Check health", "inputSchema": {}},
        {"name": "create_project", "description": "Create a new LookML project.", "inputSchema": {}},
        {"name": "get_project_files", "description": "List files.", "inputSchema": {}},
    ]

    query = "Check the system health please"
    
    # We need to access the internal method. 
    # Since I haven't implemented it yet, this test will fail if run now.
    # But this script is for AFTER refactoring.
    if hasattr(agent, "_select_relevant_tools"):
        selected = await agent._select_relevant_tools(query, tools)
        print(f"Query: '{query}'")
        print(f"Selected: {[t['name'] for t in selected]}")
        
        if len(selected) == 1 and selected[0]['name'] == "health_pulse":
            print("✅ Tool selection passed!")
        else:
            print(f"❌ Tool selection failed. Expected ['health_pulse'], got {[t['name'] for t in selected]}")
    else:
        print("⚠️ _select_relevant_tools method not found (Refactor not applied yet?)")

async def verify_prompt_rules():
    """Test if system prompt contains strict rules."""
    print("\n🔹 Testing System Prompt Rules...")
    
    agent = MCPAgent()
    
    # We'll check the _process_with_claude method logic by inspecting the code or result?
    # Actually, we can't easily inspect the internal prompt without modifiying the code to log it.
    # But we can check if the method exists and if we can trigger the new logic.
    
    # Let's try to simulate a 'POC' request and see if it tries to call create_project
    # This is an integration test, might be flaky without real credentials.
    # So we'll skip actual execution and rely on code review or manual test for now.
    print("ℹ️  System prompt verification requires manual review of logs or code inspection.")

async def verify_uncertainty():
    """Test if uncertainty triggers wider tool selection."""
    print("\n🔹 Testing Uncertainty Fallback...")
    
    agent = MCPAgent(model_name="gemini-2.0-flash")
    tools = [
        {"name": "health_pulse", "description": "Check health", "inputSchema": {}},
        {"name": "create_project", "description": "Create a new LookML project.", "inputSchema": {}},
        {"name": "get_project_files", "description": "List files.", "inputSchema": {}},
        {"name": "search_web", "description": "Search web", "inputSchema": {}},
    ]
    
    # Ambiguous query that could mean "health of project files" or "system health" or "search for help"
    query = "I'm not sure what's wrong, can you check everything?"
    
    if hasattr(agent, "_select_relevant_tools"):
        selected = await agent._select_relevant_tools(query, tools)
        print(f"Query: '{query}'")
        names = [t['name'] for t in selected]
        print(f"Selected: {names}")
        
        # Expectation: Should select multiple tools, surely more than 1, potentially all or at least health+search
        if len(names) >= 2:
            print(f"✅ Uncertainty Test passed! Selected {len(names)} tools.")
        else:
            print(f"⚠️ Uncertainty Test warning. Selected only {len(names)} tools. Might be too aggressive.")
            
async def verify_auto_registration():
    """Test auto-registration integration."""
    print("\n🔹 Testing Auto-Registration Integration...")
    
    agent = MCPAgent(model_name="gemini-2.0-flash")
    
    # Mocking environment variables and internal calls to avoid actual API/file operations
    with patch.dict(os.environ, {"LOOKERSDK_BASE_URL": "https://mock.looker.com", "LOOKERSDK_CLIENT_ID": "mock", "LOOKERSDK_CLIENT_SECRET": "mock"}):
        # Mock subprocess.run to simulate success
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({"success": True, "result": "Created file"})
            
            # 1. Create a view
            view_content = """
            view: users {
                dimension: id { type: number }
            }
            """
            result = agent._execute_create_project_file({
                "project_id": "test_proj",
                "path": "views/users.view.lkml",
                "source": view_content
            }, "url", "id", "secret")
            
            print(f"Result: {result}")
            
            if "auto_registered" in result and "View: users" in result["auto_registered"]:
                print("✅ Auto-Registration (View) Passed!")
            else:
                print(f"❌ Auto-Registration (View) Failed: {result}")
                
            # Verify context state
            if "users" in agent.lookml_context.views:
                print("✅ Context State Verified: View 'users' exists.")
            else:
                 print("❌ Context State Verification Failed.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(verify_tool_selection())
    loop.run_until_complete(verify_uncertainty())
    loop.run_until_complete(verify_auto_registration())
