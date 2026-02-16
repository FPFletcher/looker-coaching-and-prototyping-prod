"""
Database Metadata Discovery Test Script

This script tests the get_connection_tables and get_connection_columns tools
with the actual BigQuery connection to identify and fix the issues.

Test Environment:
- Connection: googlesheetcsv
- Schema: lookerpoc
- Database: BigQuery (playground-adnan)
- Known tables: Actual_Target, dim_kpi_normalized, expansion_readiness, 
                KSA_location, overall_data, trend_analysis, trend_analysis_view
"""

import asyncio
import sys
import os
import looker_sdk
from looker_sdk import models40

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.agent.mcp_agent import MCPAgent

# Test credentials
LOOKER_URL = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
CLIENT_ID = "vQyY8tbjsT6tcG7ZV85N"
CLIENT_SECRET = "hyPbyWkJXDz8h6tGcYk5Y44G"

# Test parameters
CONNECTION_NAME = "googlesheetcsv"
SCHEMA_NAME = "lookerpoc"
KNOWN_TABLES = [
    "Actual_Target",
    "dim_kpi_normalized", 
    "expansion_readiness",
    "KSA_location",
    "overall_data",
    "trend_analysis",
    "trend_analysis_view"
]

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_direct_sdk():
    """Test using Looker SDK directly to understand the API behavior"""
    print_section("TEST 1: Direct Looker SDK - Understanding API Behavior")
    
    try:
        # Initialize SDK
        os.environ["LOOKERSDK_BASE_URL"] = LOOKER_URL
        os.environ["LOOKERSDK_CLIENT_ID"] = CLIENT_ID
        os.environ["LOOKERSDK_CLIENT_SECRET"] = CLIENT_SECRET
        os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
        
        sdk = looker_sdk.init40()
        
        # Test 1: Get connection info
        print(f"📋 Testing connection: {CONNECTION_NAME}")
        try:
            connection = sdk.connection(CONNECTION_NAME)
            print(f"✅ Connection found:")
            print(f"   Name: {connection.name}")
            print(f"   Dialect: {connection.dialect.name if connection.dialect else 'unknown'}")
            print(f"   Host: {connection.host}")
            print(f"   Database: {connection.database}")
        except Exception as e:
            print(f"❌ Failed to get connection: {e}")
            return False
        
        # Test 2: Get schemas
        print(f"\n📋 Testing schemas for connection: {CONNECTION_NAME}")
        try:
            schemas = sdk.connection_schemas(CONNECTION_NAME)
            print(f"✅ Found {len(schemas)} schemas:")
            for schema in schemas[:10]:  # Show first 10
                print(f"   - {schema.name}")
            
            # Check if our schema exists
            schema_names = [s.name for s in schemas]
            if SCHEMA_NAME in schema_names:
                print(f"\n✅ Target schema '{SCHEMA_NAME}' found!")
            else:
                print(f"\n⚠️  Target schema '{SCHEMA_NAME}' NOT found in list")
                print(f"   Available schemas: {schema_names[:5]}...")
        except Exception as e:
            print(f"❌ Failed to get schemas: {e}")
            return False
        
        # Test 3: Get tables - Try different parameter formats
        print(f"\n📋 Testing tables for schema: {SCHEMA_NAME}")
        
        # Try 1: Using schema_name parameter
        print("\n  Attempt 1: Using schema_name parameter")
        try:
            tables = sdk.connection_tables(CONNECTION_NAME, schema_name=SCHEMA_NAME)
            print(f"  ✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"     - {table.name} (schema: {table.schema_name})")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Try 2: Using database_name parameter (some dialects use this)
        print("\n  Attempt 2: Using database_name parameter")
        try:
            tables = sdk.connection_tables(CONNECTION_NAME, database_name=SCHEMA_NAME)
            print(f"  ✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"     - {table.name}")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Try 3: No parameters (get all tables)
        print("\n  Attempt 3: No schema filter (get all tables)")
        try:
            tables = sdk.connection_tables(CONNECTION_NAME)
            print(f"  ✅ Found {len(tables)} total tables")
            
            # Filter by schema manually
            schema_tables = [t for t in tables if t.schema_name == SCHEMA_NAME]
            print(f"  ✅ Tables in '{SCHEMA_NAME}' schema: {len(schema_tables)}")
            for table in schema_tables:
                print(f"     - {table.name}")
                
            # Check for known tables
            table_names = [t.name for t in schema_tables]
            print(f"\n  📊 Checking for known tables:")
            for known_table in KNOWN_TABLES:
                if known_table in table_names:
                    print(f"     ✅ {known_table} - FOUND")
                else:
                    print(f"     ❌ {known_table} - NOT FOUND")
                    
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Get columns for a known table
        print(f"\n📋 Testing columns for tables")
        
        # Get tables first
        try:
            all_tables = sdk.connection_tables(CONNECTION_NAME)
            schema_tables = [t for t in all_tables if t.schema_name == SCHEMA_NAME]
            
            if schema_tables:
                test_table = schema_tables[0]
                print(f"\n  Testing with table: {test_table.name}")
                
                # Try different parameter combinations
                print(f"\n  Attempt 1: schema_name + table_name")
                try:
                    columns = sdk.connection_columns(
                        CONNECTION_NAME,
                        schema_name=SCHEMA_NAME,
                        table_name=test_table.name
                    )
                    print(f"  ✅ Found {len(columns)} columns:")
                    for col in columns[:5]:  # Show first 5
                        print(f"     - {col.name} ({col.column_type})")
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                
                print(f"\n  Attempt 2: database_name + table_name")
                try:
                    columns = sdk.connection_columns(
                        CONNECTION_NAME,
                        database_name=SCHEMA_NAME,
                        table_name=test_table.name
                    )
                    print(f"  ✅ Found {len(columns)} columns:")
                    for col in columns[:5]:
                        print(f"     - {col.name} ({col.column_type})")
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                
                print(f"\n  Attempt 3: cache parameter")
                try:
                    columns = sdk.connection_columns(
                        CONNECTION_NAME,
                        schema_name=SCHEMA_NAME,
                        table_name=test_table.name,
                        cache=False  # Force fresh data
                    )
                    print(f"  ✅ Found {len(columns)} columns:")
                    for col in columns[:5]:
                        print(f"     - {col.name} ({col.column_type})")
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                    
        except Exception as e:
            print(f"❌ Failed to test columns: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct SDK test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mcp_agent():
    """Test using MCP Agent to see how it behaves"""
    print_section("TEST 2: MCP Agent - Current Implementation")
    
    try:
        agent = MCPAgent()
        
        # Test get_connection_tables
        print(f"📋 Testing get_connection_tables")
        result = await agent.execute_tool(
            "get_connection_tables",
            {
                "connection_name": CONNECTION_NAME,
                "schema_name": SCHEMA_NAME
            },
            LOOKER_URL,
            CLIENT_ID,
            CLIENT_SECRET
        )
        
        if result.get("success"):
            tables = result.get("result", [])
            print(f"✅ Success! Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
                
            # Check for known tables
            print(f"\n📊 Checking for known tables:")
            for known_table in KNOWN_TABLES:
                if known_table in tables:
                    print(f"   ✅ {known_table} - FOUND")
                else:
                    print(f"   ❌ {known_table} - NOT FOUND")
        else:
            print(f"❌ Failed: {result.get('error')}")
        
        # Test get_connection_columns with a known table
        print(f"\n📋 Testing get_connection_columns")
        for test_table in KNOWN_TABLES[:2]:  # Test first 2 tables
            print(f"\n  Testing table: {test_table}")
            result = await agent.execute_tool(
                "get_connection_columns",
                {
                    "connection_name": CONNECTION_NAME,
                    "schema_name": SCHEMA_NAME,
                    "table_name": test_table
                },
                LOOKER_URL,
                CLIENT_ID,
                CLIENT_SECRET
            )
            
            if result.get("success"):
                columns = result.get("result", [])
                print(f"  ✅ Success! Found {len(columns)} columns:")
                for col in columns[:5]:  # Show first 5
                    print(f"     - {col.get('name')} ({col.get('sql_type')})")
            else:
                print(f"  ❌ Failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ MCP Agent test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("\n" + "="*80)
    print("  DATABASE METADATA DISCOVERY DIAGNOSTIC")
    print("="*80)
    print(f"\nConnection: {CONNECTION_NAME}")
    print(f"Schema: {SCHEMA_NAME}")
    print(f"Known Tables: {', '.join(KNOWN_TABLES)}")
    
    # Run direct SDK tests
    sdk_success = test_direct_sdk()
    
    if not sdk_success:
        print("\n⚠️  Direct SDK tests failed. Fix SDK connection first.")
        return
    
    # Run MCP agent tests
    print("\n" + "="*80)
    asyncio.run(test_mcp_agent())
    
    print("\n" + "="*80)
    print("  DIAGNOSTIC COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    # Set mock API key for agent initialization
    os.environ["GOOGLE_API_KEY"] = "mock_key_for_testing"
    main()
