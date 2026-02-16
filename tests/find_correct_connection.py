"""
Find the correct connection and schema for the user's BigQuery data

This script searches all connections and schemas to find where the 
'lookerpoc' schema and known tables exist.
"""

import looker_sdk
import os

os.environ['LOOKERSDK_BASE_URL'] = 'https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app'
os.environ['LOOKERSDK_CLIENT_ID'] = 'vQyY8tbjsT6tcG7ZV85N'
os.environ['LOOKERSDK_CLIENT_SECRET'] = 'hyPbyWkJXDz8h6tGcYk5Y44G'
os.environ['LOOKERSDK_VERIFY_SSL'] = 'true'

sdk = looker_sdk.init40()

TARGET_SCHEMA = "lookerpoc"
KNOWN_TABLES = [
    "Actual_Target",
    "dim_kpi_normalized",
    "expansion_readiness",
    "KSA_location",
    "overall_data",
    "trend_analysis",
    "trend_analysis_view"
]

print("="*80)
print("  SEARCHING FOR CORRECT CONNECTION AND SCHEMA")
print("="*80)
print(f"\nTarget Schema: {TARGET_SCHEMA}")
print(f"Known Tables: {', '.join(KNOWN_TABLES[:3])}...")

connections = sdk.all_connections()

print(f"\n📋 Checking {len(connections)} connections...\n")

for conn in connections:
    print(f"\n🔍 Connection: {conn.name}")
    print(f"   Dialect: {conn.dialect.name if conn.dialect else 'unknown'}")
    print(f"   Database: {conn.database}")
    
    try:
        # Get schemas for this connection
        schemas = sdk.connection_schemas(conn.name)
        schema_names = [s.name for s in schemas if s.name]
        
        print(f"   Schemas ({len(schema_names)}): {', '.join(schema_names[:5])}{'...' if len(schema_names) > 5 else ''}")
        
        # Check if target schema exists
        if TARGET_SCHEMA in schema_names:
            print(f"\n   ✅ FOUND TARGET SCHEMA: {TARGET_SCHEMA}")
            print(f"   🔍 Checking for tables...")
            
            # Get all tables for this connection
            try:
                all_tables = sdk.connection_tables(conn.name)
                
                # Filter by our schema
                schema_tables = [t for t in all_tables if t.schema_name == TARGET_SCHEMA]
                
                print(f"   📊 Found {len(schema_tables)} tables in '{TARGET_SCHEMA}':")
                for table in schema_tables:
                    is_known = "✅" if table.name in KNOWN_TABLES else "  "
                    print(f"      {is_known} {table.name}")
                
                # Check how many known tables we found
                found_tables = [t.name for t in schema_tables if t.name in KNOWN_TABLES]
                print(f"\n   📈 Match: {len(found_tables)}/{len(KNOWN_TABLES)} known tables found")
                
                if len(found_tables) > 0:
                    print(f"\n   🎯 THIS IS LIKELY THE CORRECT CONNECTION!")
                    print(f"\n   ✅ Use these parameters:")
                    print(f"      connection_name: {conn.name}")
                    print(f"      schema_name: {TARGET_SCHEMA}")
                    
                    # Test getting columns for first table
                    if schema_tables:
                        test_table = schema_tables[0]
                        print(f"\n   🔍 Testing column retrieval for: {test_table.name}")
                        try:
                            columns = sdk.connection_columns(
                                conn.name,
                                schema_name=TARGET_SCHEMA,
                                table_name=test_table.name
                            )
                            print(f"   ✅ Successfully retrieved {len(columns)} columns:")
                            for col in columns[:5]:
                                print(f"      - {col.name} ({col.column_type})")
                        except Exception as e:
                            print(f"   ❌ Column retrieval failed: {e}")
                
            except Exception as e:
                print(f"   ❌ Failed to get tables: {e}")
                
    except Exception as e:
        print(f"   ❌ Failed to get schemas: {e}")

print("\n" + "="*80)
print("  SEARCH COMPLETE")
print("="*80 + "\n")
