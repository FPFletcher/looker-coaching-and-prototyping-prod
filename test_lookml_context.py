#!/usr/bin/env python3
"""
Test LookML Context Tracking end-to-end
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("apps/agent/.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_lookml_context_tracking():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print("=" * 80)
    print("TESTING LOOKML CONTEXT TRACKING END-TO-END")
    print("=" * 80)
    
    # Step 1: Create a view file
    print("\n1. Creating view file...")
    view_content = """
view: test_users {
  sql_table_name: public.users ;;
  
  dimension: user_id {
    type: number
    primary_key: yes
    sql: ${TABLE}.user_id ;;
  }
  
  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
  }
  
  dimension: email {
    type: string
    sql: ${TABLE}.email ;;
  }
  
  measure: count {
    type: count
    label: "User Count"
  }
  
  measure: count_distinct {
    type: count_distinct
    sql: ${user_id} ;;
  }
}
"""
    
    result = await agent.execute_tool(
        "create_project_file",
        {
            "project_id": "antigravity_automatic_poc",
            "path": "test_users.view.lkml",
            "source": view_content
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ View file created")
    else:
        print(f"❌ View creation failed: {result.get('error')}")
        return
    
    # Step 2: Create a model file
    print("\n2. Creating model file...")
    model_content = """
connection: "bigquery_public_data"

include: "*.view.lkml"

explore: test_users {}
"""
    
    result = await agent.execute_tool(
        "create_project_file",
        {
            "project_id": "antigravity_automatic_poc",
            "path": "test_context.model.lkml",
            "source": model_content
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ Model file created")
    else:
        print(f"❌ Model creation failed: {result.get('error')}")
        return
    
    # Step 3: Check context summary
    print("\n3. Checking context summary...")
    summary = agent.lookml_context.get_summary()
    print(f"   Views: {summary['views']}")
    print(f"   Models: {summary['models']}")
    print(f"   Explores: {summary['explores']}")
    print(f"   Total fields: {summary['total_fields']}")
    
    # Step 4: Create query from context
    print("\n4. Creating query from context...")
    result = await agent.execute_tool(
        "create_query_from_context",
        {
            "model": "test_context",
            "explore": "test_users",
            "dimensions": ["user_id", "name"],
            "measures": ["count"],
            "limit": 10
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ Query created from context!")
        print(f"   Query ID: {result.get('query_id')}")
        print(f"   Fields used: {result.get('fields_used')}")
        print(f"   Context summary: {result.get('context_summary')}")
    else:
        print(f"❌ Query creation failed: {result.get('error')}")
    
    # Step 5: Test error handling - invalid field
    print("\n5. Testing error handling (invalid field)...")
    result = await agent.execute_tool(
        "create_query_from_context",
        {
            "model": "test_context",
            "explore": "test_users",
            "dimensions": ["invalid_field"],
            "measures": ["count"]
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if not result.get("success"):
        print(f"✅ Error handling works: {result.get('error')}")
    else:
        print(f"❌ Should have failed with invalid field")
    
    # Step 6: Test error handling - invalid explore
    print("\n6. Testing error handling (invalid explore)...")
    result = await agent.execute_tool(
        "create_query_from_context",
        {
            "model": "test_context",
            "explore": "nonexistent_explore",
            "dimensions": ["user_id"],
            "measures": ["count"]
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if not result.get("success"):
        print(f"✅ Error handling works: {result.get('error')}")
    else:
        print(f"❌ Should have failed with invalid explore")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_lookml_context_tracking())
