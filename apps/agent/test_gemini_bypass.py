import asyncio
from mcp_agent import MCPAgent

async def main():
    agent = MCPAgent(
        model_name="gemini-2.5-pro",
        session_id="test_byas_session"
    )
    print("Gemini Agent Client Init Check Result: NO EXCEPTION")
    print(f"Is using Vertex: {agent.is_vertex}")
    # Verify exact model matching
    print(f"Mapped Model: {agent.model}")

if __name__ == "__main__":
    asyncio.run(main())
