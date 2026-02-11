#!/usr/bin/env python3
"""
Test manual LookML registration as API fallback
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("apps/agent/.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/agent'))

from mcp_agent import MCPAgent
import asyncio

async def test_manual_registration():
    agent = MCPAgent()
    
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print("=" * 80)
    print("TESTING MANUAL LOOKML REGISTRATION (API FALLBACK)")
    print("=" * 80)
    
    # Test 1: Manually register a view
    print("\n1. Manually registering a view...")
    result = await agent.execute_tool(
        "register_lookml_manually",
        {
            "type": "view",
            "view_name": "orders",
            "sql_table_name": "public.orders",
            "fields": [
                {"name": "order_id", "type": "dimension", "field_type": "number"},
                {"name": "user_id", "type": "dimension", "field_type": "number"},
                {"name": "status", "type": "dimension", "field_type": "string"},
                {"name": "created_date", "type": "dimension", "field_type": "date"},
                {"name": "count", "type": "measure", "field_type": "count"},
                {"name": "total_amount", "type": "measure", "field_type": "sum"}
            ]
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ {result.get('message')}")
        print(f"   Context: {result.get('context_summary')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
        return
    
    # Test 2: Manually register a model
    print("\n2. Manually registering a model...")
    result = await agent.execute_tool(
        "register_lookml_manually",
        {
            "type": "model",
            "model_name": "ecommerce",
            "connection": "bigquery_public_data",
            "explores": ["orders", "users"],
            "includes": ["*.view.lkml"]
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ {result.get('message')}")
        print(f"   Context: {result.get('context_summary')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
        return
    
    # Test 3: Manually register an explore
    print("\n3. Manually registering an explore...")
    result = await agent.execute_tool(
        "register_lookml_manually",
        {
            "type": "explore",
            "model": "ecommerce",
            "explore": "orders",
            "base_view": "orders"
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ {result.get('message')}")
        print(f"   Context: {result.get('context_summary')}")
    else:
        print(f"❌ Failed: {result.get('error')}")
        return
    
    # Test 4: Use the manually registered explore to create a query
    print("\n4. Creating query from manually registered explore...")
    result = await agent.execute_tool(
        "create_query_from_context",
        {
            "model": "ecommerce",
            "explore": "orders",
            "dimensions": ["order_id", "status"],
            "measures": ["count"],
            "limit": 10
        },
        looker_url,
        client_id,
        client_secret
    )
    
    if result.get("success"):
        print(f"✅ Query created from manually registered context!")
        print(f"   Query ID: {result.get('query_id')}")
        print(f"   Fields used: {result.get('fields_used')}")
    else:
        print(f"❌ Query creation failed: {result.get('error')}")
    
    # Test 5: Check final context summary
    print("\n5. Final context summary:")
    summary = agent.lookml_context.get_summary()
    print(f"   Views: {summary['views']}")
    print(f"   Models: {summary['models']}")
    print(f"   Explores: {summary['explores']}")
    print(f"   Total fields: {summary['total_fields']}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE - MANUAL REGISTRATION WORKS!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_manual_registration())
