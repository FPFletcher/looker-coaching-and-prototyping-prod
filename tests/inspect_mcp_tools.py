import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from apps.agent.mcp_agent import MCPAgent

async def main():
    agent = MCPAgent(session_id="test", model_name="gemini-2.0-flash")
    tools = await agent.list_available_tools(looker_url="https://demo.looker.com", client_id="test", client_secret="test")
    for t in tools:
        if t["name"] == "get_explore_fields":
            print(t)

asyncio.run(main())
