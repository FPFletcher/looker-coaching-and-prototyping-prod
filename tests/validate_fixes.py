
import sys
import os
import asyncio
import logging
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.agent.mcp_agent import MCPAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixes():
    print("\n--- STARTING VALIDATION ---")
    
    # Set dummy keys for initialization
    os.environ["GOOGLE_API_KEY"] = "dummy"
    os.environ["ANTHROPIC_API_KEY"] = "dummy"
    
    agent = MCPAgent()
    
    # Mock URL/Creds
    url = "https://example.looker.com"
    cid = "client_id"
    sec = "client_secret"

    # 1. Test create_project_file path resolution
    # We can't actually run the deploy script without credentials/real connection,
    # but we can check if the file path logic works or if it immediately errors on "script not found".
    # Since we can't easily mock the subprocess call here without extensive mocking, 
    # we'll rely on the user report or manual check. 
    # BUT we can check if the script exists at the new path!
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../scripts/deploy_lookml.py"))
    if os.path.exists(script_path):
        print(f"✅ deploy_lookml.py found at {script_path}")
    else:
        print(f"❌ deploy_lookml.py NOT found at {script_path}")

    # 2. Test search_web
    print("\n--- Testing search_web ---")
    search_res = agent._execute_search_web({"query": "python asyncio"})
    if search_res.get("success"):
        print(f"✅ search_web returned success. Result type: {type(search_res.get('result'))}")
        # print(search_res.get("result"))
    else:
        print(f"❌ search_web failed: {search_res.get('error')}")

    # 3. Test Strict POC Mode
    print("\n--- Testing Strict POC Mode (Mode: OFF) ---")
    # Simulate process_message setting poc_mode=False
    agent.poc_mode = False
    
    # Try register_lookml_manually
    reg_res = agent._execute_register_lookml_manually({"type": "view", "code": "view: foo {}"}, url, cid, sec)
    if not reg_res.get("success") and "POC Mode" in reg_res.get("error", ""):
        print("✅ register_lookml_manually BLOCKED correctly in prod mode")
    else:
        print(f"❌ register_lookml_manually NOT blocked or unexpected error: {reg_res}")

    # Try create_chart_from_context
    chart_res = agent._execute_create_chart_from_context({"model": "foo"}, url, cid, sec)
    if not chart_res.get("success") and "POC Mode" in chart_res.get("error", ""):
        print("✅ create_chart_from_context BLOCKED correctly in prod mode")
    else:
        print(f"❌ create_chart_from_context NOT blocked or unexpected error: {chart_res}")

    print("\n--- END VALIDATION ---")

if __name__ == "__main__":
    asyncio.run(test_fixes())
