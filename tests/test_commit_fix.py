#!/usr/bin/env python3
"""
Test the fixed commit_project_changes implementation
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("apps/agent/.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_commit_fix():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print("=" * 80)
    print("TESTING FIXED COMMIT IMPLEMENTATION")
    print("=" * 80)
    
    # Test commit_project_changes
    print("\nTesting commit_project_changes...")
    result = await agent.execute_tool(
        "commit_project_changes",
        {
            "project_id": "antigravity_automatic_poc_version_2",
            "message": "Test commit from fixed implementation"
        },
        looker_url,
        client_id,
        client_secret
    )
    
    print(f"\nResult:")
    print(f"  Success: {result.get('success')}")
    if result.get('success'):
        print(f"  ✅ Commit succeeded!")
        print(f"  Commit SHA: {result.get('commit_sha')}")
        print(f"  Message: {result.get('message')}")
    else:
        print(f"  ❌ Commit failed")
        print(f"  Error: {result.get('error')}")
        
        # If it's a 403, explain why
        if "403" in str(result.get('error')):
            print(f"\n  Note: 403 Forbidden likely means:")
            print(f"    - Project is a bare repo (no git remote configured)")
            print(f"    - User doesn't have commit permissions")
            print(f"    - Need to be in dev mode first")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_commit_fix())
