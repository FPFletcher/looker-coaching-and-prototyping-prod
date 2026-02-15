
import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "apps", "agent"))

from apps.agent.mcp_agent import MCPAgent

def test_dashboard_creation():
    """Reproduce 404 and find fix."""
    print("Initializing Agent...")
    
    # Mock environment for Agent init
    import os
    os.environ["GOOGLE_API_KEY"] = "mock_key"
    os.environ["ANTHROPIC_API_KEY"] = "mock_key"
    
    # We also need Looker creds for the SDK init
    # Assuming they are in the user's env or passed in Args
    # If not, we can't really test without them. 
    # But usually user has them in env, let's print if they exist
    print(f"Looker URL in Env: {os.environ.get('LOOKERSDK_BASE_URL', 'Not Set')}")
    
    try:
        agent = MCPAgent(model_name="gemini-2.0-flash")
    except Exception as e:
        print(f"Agent mock init failed (ignoring): {e}")
        # Proceed to test SDK directly if Agent fails (we just need SDK logic)
    
    # We need real creds for this to hit the API (since it's a 404 from the API)
    # But I don't have them in the env? The agent has them passed in execute_tool.
    # The user environment has them. I will assume os.environ has them or search for them.
    # Wait, the verification script runs in the user's environment.
    
    # Let's try to instantiate Looker SDK directly if possible, or use the agent's methods.
    # But agent._execute_create_dashboard needs url, client_id, client_secret.
    # I can try to find them in the environment or simple use the agent's _init_sdk if I can mock the args.
    
    # CHECK ENV
    import looker_sdk
    try:
        sdk = looker_sdk.init40()
        print("SDK Initialized successfully from Env.")
    except Exception as e:
        print(f"SDK Init failed: {e}")
        return

    # 1. Try to list folders (to find 'Shared')
    try:
        folders = sdk.all_folders()
        print(f"Found {len(folders)} folders.")
        shared = next((f for f in folders if f.name == 'Shared'), None)
        personal = next((f for f in folders if f.is_personal), None)
        
        if shared:
            print(f"Shared Folder: {shared.id} ({shared.name})")
        if personal:
            print(f"Personal Folder: {personal.id} ({personal.name})")
            
    except Exception as e:
        print(f"Failed to list folders: {e}")

    # 2. Try to create dashboard WITHOUT folder (repro failure)
    print("\n--- Attempting Create WITHOUT Folder ---")
    try:
        from looker_sdk import models40
        dash = sdk.create_dashboard(models40.WriteDashboard(title="Test No Folder"))
        print(f"SUCCESS: Created dashboard {dash.id}")
    except Exception as e:
        print(f"FAILURE (Expected): {e}")

    # 3. Try to create dashboard WITH Personal Folder
    if personal:
        print("\n--- Attempting Create WITH Personal Folder ---")
        try:
            dash = sdk.create_dashboard(models40.WriteDashboard(title="Test Personal Folder", folder_id=personal.id))
            print(f"SUCCESS: Created dashboard {dash.id}")
            # Clean up
            sdk.delete_dashboard(dash.id)
            print("Cleaned up.")
        except Exception as e:
            print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_dashboard_creation()
