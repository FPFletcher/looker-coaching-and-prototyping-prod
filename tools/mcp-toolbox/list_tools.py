import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

async def list_tools():
    # We connect to the toolbox via stdio or SSE. 
    # Since it is running as a server on port 5000, we should use SSE client if MCP supports it,
    # or just run a temporary stdio client to check.
    # The server mode is for remote clients.
    
    # Let's try to run it as a subprocess client for introspection, 
    # as connecting to the running HTTP server via python-mcp might be complex without the specific SSE transport.
    
    server_params = StdioServerParameters(
        command="./toolbox",
        args=["start", "--prebuilt", "looker"],
        env={
            "LOOKER_BASE_URL": "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
            "LOOKER_CLIENT_ID": "vQyY8tbjsT6tcG7ZV85N",
            "LOOKER_CLIENT_SECRET": "hyPbyWkJXDz8h6tGcYk5Y44G",
            "LOOKER_VERIFY_SSL": "true"
        }
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                tools = await session.list_tools()
                print("--- Available Tools ---")
                for tool in tools.tools:
                    print(f"Name: {tool.name}")
                    print(f"Description: {tool.description}")
                    print(f"Schema: {tool.inputSchema}")
                    print("---")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Point to the right cwd
    os.chdir("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/tools/mcp-toolbox")
    asyncio.run(list_tools())
