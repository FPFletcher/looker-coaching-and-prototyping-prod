#!/usr/bin/env python3
"""
Test the new LookML validation and model discovery tools
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("apps/agent/.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_new_tools():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print("=" * 80)
    print("TESTING NEW LOOKML VALIDATION TOOLS")
    print("=" * 80)
    
    # Test 1: Enhanced get_models
    print("\n1. Testing enhanced get_models (with workspace info)...")
    result = await agent.execute_tool(
        "get_models",
        {},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        print(f"✅ Success!")
        print(f"   Workspace: {result.get('workspace')}")
        print(f"   Models found: {len(result.get('models', []))}")
        if result.get('models'):
            print(f"   First model: {result['models'][0]['name']} (explores: {len(result['models'][0].get('explores', []))})")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 2: Validate project
    print("\n2. Testing validate_project...")
    result = await agent.execute_tool(
        "validate_project",
        {"project_id": "antigravity_automatic_poc"},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        if result.get("valid"):
            print(f"✅ Project validation passed!")
        else:
            print(f"⚠️  Project has validation errors:")
            for error in result.get("errors", []):
                print(f"   - {error.get('file_path')}: {error.get('message')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 3: Get specific explore
    print("\n3. Testing get_lookml_model_explore...")
    result = await agent.execute_tool(
        "get_lookml_model_explore",
        {"model_name": "thelook", "explore_name": "orders"},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        if result.get("exists"):
            explore = result.get("explore", {})
            print(f"✅ Explore found!")
            print(f"   Name: {explore.get('name')}")
            print(f"   Model: {explore.get('model_name')}")
            print(f"   Dimensions: {explore.get('dimensions_count')}")
            print(f"   Measures: {explore.get('measures_count')}")
        else:
            print(f"⚠️  Explore not found")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    # Test 4: Enhanced dev_mode
    print("\n4. Testing enhanced dev_mode...")
    result = await agent.execute_tool(
        "dev_mode",
        {"enable": True},
        looker_url,
        client_id,
        client_secret
    )
    if result.get("success"):
        print(f"✅ Dev mode enabled!")
        print(f"   Workspace: {result.get('workspace')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_new_tools())
