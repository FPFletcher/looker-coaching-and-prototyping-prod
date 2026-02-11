#!/usr/bin/env python3
"""
Test validation workflow and field verification
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv("apps/agent/.env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_validation_and_fields():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    project_id = "antigravity_automatic_poc"
    
    print("=" * 80)
    print("TESTING VALIDATION WORKFLOW & FIELD VERIFICATION")
    print("=" * 80)
    
    # Test 1: Create valid LookML and check validation
    print("\n1. Creating valid LookML file...")
    view_content = """
view: validation_test {
  sql_table_name: public.users ;;
  
  dimension: id {
    type: number
    primary_key: yes
    sql: ${TABLE}.id ;;
  }
  
  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
  }
  
  measure: count {
    type: count
  }
}
"""
    
    result = await agent.execute_tool(
        "create_project_file",
        {
            "project_id": project_id,
            "path": "validation_test.view.lkml",
            "source": view_content
        },
        looker_url,
        client_id,
        client_secret
    )
    
    print(f"\n   Result: {result.get('message')}")
    print(f"   Validation passed: {result.get('validation_passed')}")
    print(f"   Prompt commit: {result.get('prompt_commit')}")
    if result.get('validation_errors'):
        print(f"   Errors: {result.get('validation_errors')}")
    
    # Test 2: Test get_explore_fields
    print("\n2. Testing get_explore_fields...")
    result = await agent.execute_tool(
        "get_explore_fields",
        {
            "model": "ecommerce",
            "explore": "order_items"
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"   ✅ Fetched {result.get('total_fields')} fields")
        print(f"   Dimensions: {result.get('dimensions')}")
        print(f"   Measures: {result.get('measures')}")
        print(f"   Sample fields: {result.get('available_fields', [])[:10]}")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    # Test 3: Check context has API-verified fields
    print("\n3. Checking context for API-verified fields...")
    summary = agent.lookml_context.get_summary()
    print(f"   API-verified explores: {summary.get('api_verified_explores')}")
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_validation_and_fields())
