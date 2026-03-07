import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Add agent path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_agent import MCPAgent

async def test_mapping(model_name, expect_vertex, expect_anthropic):
    print(f"\nTesting '{model_name}':")
    
    # Test Direct API (Mock)
    os.environ["ANTHROPIC_API_KEY"] = "mock_key"
    old_vc = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    old_vp = os.environ.pop("VERTEX_API_KEY", None)
    
    agent_direct = MCPAgent(model_name=model_name)
    print(f"  Direct API resolves to: {agent_direct.model_name}")
    if agent_direct.model_name != expect_anthropic:
        print(f"  [!] Direct mapping failed! Expected '{expect_anthropic}' got '{agent_direct.model_name}'")
        
    # Restore Vertex Environment
    if old_vc: os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = old_vc
    if old_vp: os.environ["VERTEX_API_KEY"] = old_vp
    os.environ.pop("ANTHROPIC_API_KEY", None)
    
    agent_vertex = MCPAgent(model_name=model_name)
    print(f"  Vertex AI resolves to: {agent_vertex.model_name}")
    if agent_vertex.model_name != expect_vertex:
        print(f"  [!] Vertex mapping failed! Expected '{expect_vertex}' got '{agent_vertex.model_name}'")

async def test_all():
    await test_mapping("claude-sonnet-4-6", "claude-sonnet-4-6@defaultclaude", "claude-sonnet-4-6")
    await test_mapping("claude-opus-4-6", "claude-opus-4-6@defaultclaude", "claude-opus-4-6")
    await test_mapping("claude-sonnet-4-5", "claude-sonnet-4-5@20250929", "claude-sonnet-4-5")
    
    # Also test the cached legacy names from the dropdown bug
    await test_mapping("claude-sonnet-4-6@defaultclaude", "claude-sonnet-4-6@defaultclaude", "claude-sonnet-4-6")
    await test_mapping("claude-opus-4-6@defaultclaude", "claude-opus-4-6@defaultclaude", "claude-opus-4-6")
    
if __name__ == "__main__":
    asyncio.run(test_all())
