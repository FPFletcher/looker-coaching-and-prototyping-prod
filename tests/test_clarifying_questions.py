#!/usr/bin/env python3
"""
Test script to verify clarifying questions are working
"""
import asyncio
import sys
sys.path.append('/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent')

from mcp_agent import MCPAgent

async def test_clarifying_questions():
    print("=" * 60)
    print("Testing Clarifying Questions")
    print("=" * 60)
    
    agent = MCPAgent(
        model_name="claude-sonnet-4-5-20250929",
        looker_url="https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
        looker_client_id="YOUR_CLIENT_ID",
        looker_client_secret="YOUR_SECRET" 
    )
    
    # Test case 1: "top 10 products" - should ask for clarification
    test_message = "find the top 10 product categories"
    
    print(f"\nTest Query: '{test_message}'")
    print("Expected: AI should ASK which metric to rank by (revenue, margin, count, etc.)")
    print("\nActual Response:")
    print("-" * 60)
    
    try:
        async for event in agent.process_message(test_message, [], explore_context=""):
            if event.get("type") == "text":
                print(event.get("content"), end="", flush=True)
            elif event.get("type") == "tool_use":
                tool_name = event.get("content", {}).get("name")
                print(f"\n[TOOL CALLED: {tool_name}]")
                # If create_chart is called WITHOUT asking, the test FAILED
                if tool_name in ["create_chart", "get_dimensions", "get_measures"]:
                    print("\n❌ FAILED: AI called tool without asking for clarification!")
                    return False
    except Exception as e:
        print(f"\nError during test: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ PASSED: AI asked for clarification before calling tools!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_clarifying_questions())
    sys.exit(0 if result else 1)
