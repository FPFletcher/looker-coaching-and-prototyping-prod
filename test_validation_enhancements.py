#!/usr/bin/env python3
"""
Test the new LookML validation enhancement tools
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("apps/agent/.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_validation_enhancements():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print("=" * 80)
    print("TESTING LOOKML VALIDATION ENHANCEMENTS")
    print("=" * 80)
    
    # Test 1: Enhanced validate_project
    print("\n1. Testing enhanced validate_project...")
    result = await agent.execute_tool(
        "validate_project",
        {"project_id": "antigravity_automatic_poc"},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        print(f"✅ Validation complete!")
        print(f"   Valid: {result.get('valid')}")
        print(f"   Models parsed: {result.get('models_parsed', [])}")
        print(f"   Errors: {len(result.get('errors', []))}")
        print(f"   Project errors: {len(result.get('project_errors', []))}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 2: Get git branch state
    print("\n2. Testing get_git_branch_state...")
    result = await agent.execute_tool(
        "get_git_branch_state",
        {"project_id": "antigravity_automatic_poc"},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        print(f"✅ Git state retrieved!")
        print(f"   Branch: {result.get('branch_name')}")
        print(f"   Uncommitted files: {len(result.get('uncommitted_files', []))}")
        if result.get('uncommitted_files'):
            for f in result['uncommitted_files'][:5]:  # Show first 5
                print(f"     - {f.get('path')} ({f.get('status')})")
        print(f"   Can commit: {result.get('can_commit')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 3: Get project structure
    print("\n3. Testing get_project_structure...")
    result = await agent.execute_tool(
        "get_project_structure",
        {"project_id": "antigravity_automatic_poc"},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        print(f"✅ Project structure analyzed!")
        print(f"   Has subdirectories: {result.get('has_subdirectories')}")
        print(f"   Recommended include: {result.get('recommended_include_pattern')}")
        print(f"   View files: {len(result.get('view_files', []))}")
        print(f"   Model files: {len(result.get('model_files', []))}")
        print(f"   Total files: {result.get('total_files')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 4: Get datagroups
    print("\n4. Testing get_datagroups...")
    result = await agent.execute_tool(
        "get_datagroups",
        {},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        datagroups = result.get('datagroups', [])
        print(f"✅ Datagroups retrieved!")
        print(f"   Total datagroups: {len(datagroups)}")
        if datagroups:
            for dg in datagroups[:5]:  # Show first 5
                print(f"     - {dg.get('name')} (model: {dg.get('model_name')})")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_validation_enhancements())
