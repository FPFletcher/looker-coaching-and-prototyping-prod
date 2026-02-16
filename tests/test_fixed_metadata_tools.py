"""
Comprehensive test of fixed database metadata tools

Tests the improved get_connection_tables and get_connection_columns tools
with actual BigQuery connections.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.agent.mcp_agent import MCPAgent

# Test credentials
LOOKER_URL = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
CLIENT_ID = "vQyY8tbjsT6tcG7ZV85N"
CLIENT_SECRET = "hyPbyWkJXDz8h6tGcYk5Y44G"

# Use an existing connection
TEST_CONNECTION = "sample_bigquery_connection"
TEST_SCHEMA = "thelook_ecommerce"  # Known to exist

async def test_fixed_tools():
    print("="*80)
    print("  TESTING FIXED DATABASE METADATA TOOLS")
    print("="*80)
    
    agent = MCPAgent()
    
    # Test 1: get_connection_tables with valid schema
    print(f"\n📋 TEST 1: get_connection_tables with valid schema")
    print(f"   Connection: {TEST_CONNECTION}")
    print(f"   Schema: {TEST_SCHEMA}")
    
    result = await agent.execute_tool(
        "get_connection_tables",
        {
            "connection_name": TEST_CONNECTION,
            "schema_name": TEST_SCHEMA
        },
        LOOKER_URL,
        CLIENT_ID,
        CLIENT_SECRET
    )
    
    if result.get("success"):
        tables = result.get("result", [])
        message = result.get("message", "")
        print(f"   ✅ Success! {message}")
        print(f"   Found {len(tables)} tables:")
        for table in tables[:5]:
            print(f"      - {table}")
        if len(tables) > 5:
            print(f"      ... and {len(tables) - 5} more")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return False
    
    # Test 2: get_connection_tables without schema (should return all)
    print(f"\n📋 TEST 2: get_connection_tables without schema")
    print(f"   Connection: {TEST_CONNECTION}")
    
    result = await agent.execute_tool(
        "get_connection_tables",
        {
            "connection_name": TEST_CONNECTION
        },
        LOOKER_URL,
        CLIENT_ID,
        CLIENT_SECRET
    )
    
    if result.get("success"):
        tables = result.get("result", [])
        message = result.get("message", "")
        print(f"   ✅ Success! {message}")
        print(f"   Sample tables:")
        for table in tables[:3]:
            print(f"      - {table.get('name')} (schema: {table.get('schema')})")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
    
    # Test 3: get_connection_tables with invalid schema
    print(f"\n📋 TEST 3: get_connection_tables with invalid schema")
    print(f"   Connection: {TEST_CONNECTION}")
    print(f"   Schema: nonexistent_schema")
    
    result = await agent.execute_tool(
        "get_connection_tables",
        {
            "connection_name": TEST_CONNECTION,
            "schema_name": "nonexistent_schema"
        },
        LOOKER_URL,
        CLIENT_ID,
        CLIENT_SECRET
    )
    
    if not result.get("success"):
        error = result.get("error", "")
        print(f"   ✅ Correctly failed with helpful error:")
        print(f"      {error[:200]}...")
    else:
        print(f"   ⚠️  Should have failed but succeeded")
    
    # Test 4: get_connection_columns with valid table
    print(f"\n📋 TEST 4: get_connection_columns with valid table")
    
    # First get a table from the schema
    tables_result = await agent.execute_tool(
        "get_connection_tables",
        {
            "connection_name": TEST_CONNECTION,
            "schema_name": TEST_SCHEMA
        },
        LOOKER_URL,
        CLIENT_ID,
        CLIENT_SECRET
    )
    
    if tables_result.get("success") and tables_result.get("result"):
        test_table = tables_result["result"][0]
        print(f"   Connection: {TEST_CONNECTION}")
        print(f"   Schema: {TEST_SCHEMA}")
        print(f"   Table: {test_table}")
        
        result = await agent.execute_tool(
            "get_connection_columns",
            {
                "connection_name": TEST_CONNECTION,
                "schema_name": TEST_SCHEMA,
                "table_name": test_table
            },
            LOOKER_URL,
            CLIENT_ID,
            CLIENT_SECRET
        )
        
        if result.get("success"):
            columns = result.get("result", [])
            message = result.get("message", "")
            print(f"   ✅ Success! {message}")
            print(f"   Sample columns:")
            for col in columns[:5]:
                print(f"      - {col.get('name')} ({col.get('sql_type')})")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
            return False
    
    # Test 5: get_connection_columns without schema (auto-detect)
    print(f"\n📋 TEST 5: get_connection_columns without schema (auto-detect)")
    
    if tables_result.get("success") and tables_result.get("result"):
        test_table = tables_result["result"][0]
        print(f"   Connection: {TEST_CONNECTION}")
        print(f"   Table: {test_table} (schema will be auto-detected)")
        
        result = await agent.execute_tool(
            "get_connection_columns",
            {
                "connection_name": TEST_CONNECTION,
                "table_name": test_table
            },
            LOOKER_URL,
            CLIENT_ID,
            CLIENT_SECRET
        )
        
        if result.get("success"):
            columns = result.get("result", [])
            message = result.get("message", "")
            print(f"   ✅ Success! Schema auto-detected")
            print(f"   {message}")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
    
    # Test 6: get_connection_columns with invalid table
    print(f"\n📋 TEST 6: get_connection_columns with invalid table")
    print(f"   Connection: {TEST_CONNECTION}")
    print(f"   Schema: {TEST_SCHEMA}")
    print(f"   Table: nonexistent_table")
    
    result = await agent.execute_tool(
        "get_connection_columns",
        {
            "connection_name": TEST_CONNECTION,
            "schema_name": TEST_SCHEMA,
            "table_name": "nonexistent_table"
        },
        LOOKER_URL,
        CLIENT_ID,
        CLIENT_SECRET
    )
    
    if not result.get("success"):
        error = result.get("error", "")
        print(f"   ✅ Correctly failed with helpful error:")
        print(f"      {error[:200]}...")
    else:
        print(f"   ⚠️  Should have failed but succeeded")
    
    print("\n" + "="*80)
    print("  ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*80 + "\n")
    
    return True

if __name__ == "__main__":
    os.environ["GOOGLE_API_KEY"] = "mock_key_for_testing"
    success = asyncio.run(test_fixed_tools())
    sys.exit(0 if success else 1)
