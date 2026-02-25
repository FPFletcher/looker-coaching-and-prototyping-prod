import sys
import os
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from apps.agent.mcp_agent import MCPAgent

agent = MCPAgent()
res = agent._execute_get_explore_fields(
    {"model_name": "marketing_returning_customers", "explore_name": "order_items"},
    "https://demo.looker.com", 
    os.getenv("LOOKERSDK_CLIENT_ID"), 
    os.getenv("LOOKERSDK_CLIENT_SECRET")
)
print(f"Success: {res.get('success')}")
if 'dimensions' in res:
    print(f"Dims: {len(res['dimensions'])}")
    print(f"First Dim: {res['dimensions'][0]}")
if 'error' in res:
    print(f"Error: {res['error']}")
