#!/usr/bin/env python3
"""
Test Git deployment workflow with version_3 project
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv("apps/agent/.env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_git_deployment():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    project_id = "antigravity_automatic_poc_version_3"
    
    print("=" * 80)
    print("TESTING GIT DEPLOYMENT WORKFLOW (VERSION_3)")
    print("=" * 80)
    
    # Step 1: Switch to dev mode
    print("\n1. Switching to dev mode...")
    result = await agent.execute_tool(
        "dev_mode",
        {"enable": True},
        looker_url,
        client_id,
        client_secret
    )
    print(f"   Result: {result}")
    
    # Step 2: Create a simple view file
    print("\n2. Creating test view file...")
    view_content = """
view: git_test_view {
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
            "path": "git_test_view.view.lkml",
            "source": view_content
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"   ✅ View file created")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return
    
    # Step 3: Create a model file
    print("\n3. Creating test model file...")
    model_content = """
connection: "bigquery_public_data"

include: "*.view.lkml"

explore: git_test_view {}
"""
    
    result = await agent.execute_tool(
        "create_project_file",
        {
            "project_id": project_id,
            "path": "git_test.model.lkml",
            "source": model_content
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"   ✅ Model file created")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return
    
    # Step 4: Check Git status
    print("\n4. Checking Git status...")
    result = await agent.execute_tool(
        "get_git_branch_state",
        {"project_id": project_id},
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"   Branch: {result.get('branch')}")
        print(f"   Uncommitted changes: {len(result.get('uncommitted_changes', []))}")
        for change in result.get('uncommitted_changes', [])[:5]:
            print(f"     - {change}")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    # Step 5: Try to commit changes
    print("\n5. Attempting to commit changes...")
    result = await agent.execute_tool(
        "commit_project_changes",
        {
            "project_id": project_id,
            "message": "Test commit from agent"
        },
        looker_url,
        client_id,
        client_secret
    )
    
    print(f"   Result: {result}")
    
    # Step 6: If commit worked, try to query
    if result.get("success"):
        print("\n6. ✅ COMMIT SUCCEEDED! Now trying to query...")
        
        # Wait a moment for deployment
        import time
        time.sleep(2)
        
        # Try standard query (should work now)
        result = await agent.execute_tool(
            "run_query",
            {
                "model": "git_test",
                "view": "git_test_view",
                "fields": ["git_test_view.id", "git_test_view.count"],
                "limit": 10
            },
            looker_url,
            client_id,
            client_secret
        )
        
        print(f"   Query result: {result}")
    else:
        print("\n6. ❌ COMMIT FAILED - Cannot query uncommitted LookML")
        print(f"   Error: {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_git_deployment())
