
import os
import sys
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add module path
sys.path.append("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects")

from apps.agent.mcp_agent import MCPAgent

def verify_root_creation():
    # Load env vars from .env for simulation
    from dotenv import load_dotenv
    load_dotenv("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/.env")
    
    # Init agent
    agent = MCPAgent()
    
    # Test Parameters
    project_id = "antigravity_automatic_poc"
    path = "customer_cdp.model.lkml" # Root path
    source = """connection: "ffrancois_-_ecomm_trial"

include: "*.view.lkml"

datagroup: customer_cdp_default_datagroup {
  sql_trigger: SELECT MAX(created_at) FROM thelook_ecommerce.orders ;;
  max_cache_age: "1 hour"
}

persist_with: customer_cdp_default_datagroup

explore: customer_360 {
  label: "Customer 360 - CDP Golden Explore"
  from: users
  view_name: users
}
"""
    
    print(f"Testing create_project_file for {path} in {project_id}...")
    
    # Execute tool (which now uses _get_raw_access_token internally)
    try:
        # Note: We pass the URL from env, which should be the clean one now
        url = os.environ.get("LOOKERSDK_BASE_URL")
        client_id = os.environ.get("LOOKERSDK_CLIENT_ID")
        client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET")
        
        print(f"Using Base URL: {url}")
        
        result = agent._execute_create_project_file(
            args={"project_id": project_id, "path": path, "source": source},
            url=url,
            client_id=client_id,
            client_secret=client_secret
        )
        print("Result:", result)
    except Exception as e:
        print("Execution Failed:", e)

if __name__ == "__main__":
    verify_root_creation()
