"""
Search for known tables across all connections and schemas

Since the 'lookerpoc' schema doesn't exist, let's find where the actual tables are.
"""

import looker_sdk
import os

os.environ['LOOKERSDK_BASE_URL'] = 'https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app'
os.environ['LOOKERSDK_CLIENT_ID'] = 'vQyY8tbjsT6tcG7ZV85N'
os.environ['LOOKERSDK_CLIENT_SECRET'] = 'hyPbyWkJXDz8h6tGcYk5Y44G'
os.environ['LOOKERSDK_VERIFY_SSL'] = 'true'

sdk = looker_sdk.init40()

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
print("  SEARCHING FOR KNOWN TABLES ACROSS ALL CONNECTIONS")
print("="*80)
print(f"\nLooking for: {', '.join(KNOWN_TABLES[:3])}...")

connections = sdk.all_connections()

for conn in connections:
    if conn.name == 'test_oauth':  # Skip OAuth
        continue
    
    print(f"\n🔍 Checking connection: {conn.name}")
    
    try:
        # Get all tables for this connection
        all_tables = sdk.connection_tables(conn.name)
        
        # Check for any of our known tables
        found_tables = []
        for table in all_tables:
            if table.name in KNOWN_TABLES:
                found_tables.append(table)
        
        if found_tables:
            print(f"\n   ✅ FOUND {len(found_tables)} MATCHING TABLES!")
            for table in found_tables:
                print(f"      - {table.name} (schema: {table.schema_name})")
            
            # Get unique schemas
            schemas = list(set([t.schema_name for t in found_tables]))
            print(f"\n   📊 Schemas containing these tables: {schemas}")
            
            # This is likely the correct connection!
            print(f"\n   🎯 CORRECT CONNECTION FOUND!")
            print(f"      connection_name: {conn.name}")
            print(f"      schema_name: {schemas[0] if len(schemas) == 1 else 'MULTIPLE - see above'}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("  SEARCH COMPLETE")
print("="*80 + "\n")
