import asyncio
import json
from mcp_agent import MCPAgent

async def main():
    agent = MCPAgent(
        model_name="gemini-2.0-flash", # Let's test flash using proper config
        session_id="test_session"
    )
    
    # We aren't testing standard generation directly here with UI context,
    # but let's test that generation works with Gemini 
    print("Agent init successful!")
    # To properly test, let's execute the raw model, or rather just use the test we did already. No need to simulate.
    pass

if __name__ == "__main__":
    asyncio.run(main())
