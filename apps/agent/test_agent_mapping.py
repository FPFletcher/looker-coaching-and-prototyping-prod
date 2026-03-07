import asyncio
import os
from mcp_agent import MCPAgent

# Mock environment variables or pass them directly
# We want to test the logic we just added.

async def test_claude_mapping():
    print("--- Testing Claude Mapping (Direct Key) ---")
    # Simulate direct key provided
    agent = MCPAgent(
        model_name="claude-3-5-sonnet-v2@20241022", # UI sends this usually or something similar
        claude_api_key="sk-ant-test-key-must-start-with-sk", 
        vertex_api_key=""
    )
    
    print(f"Is Vertex: {agent.is_vertex}")
    print(f"Model Name: {agent.model_name}")
    
    if agent.is_vertex == False and agent.model_name == "claude-3-5-sonnet-20241022":
        print("SUCCESS: mapped to correct Anthropic model.")
    else:
        print("FAILURE: Incorrect mapping or vertex state.")

async def test_gemini_mapping():
    print("\n--- Testing Gemini Mapping (Direct Key) ---")
    # Simulate direct key provided (starts with AIza)
    agent = MCPAgent(
        model_name="gemini-2.5-flash-lite", 
        vertex_api_key="AIza-test-key",
        claude_api_key=""
    )
    
    print(f"Is Vertex: {agent.is_vertex}")
    print(f"Model Name: {agent.model_name}")
    
    if agent.is_vertex == False and agent.model_name == "gemini-2.5-flash-lite":
        print("SUCCESS: mapped to correct Gemini model (standard).")
    else:
        print("FAILURE: Incorrect mapping or vertex state.")

if __name__ == "__main__":
    asyncio.run(test_claude_mapping())
    asyncio.run(test_gemini_mapping())
