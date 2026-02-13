#!/usr/bin/env python3
"""
Use Looker SDK to retrieve file content
"""
import os
import sys
import looker_sdk

os.environ["LOOKERSDK_BASE_URL"] = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
os.environ["LOOKERSDK_CLIENT_ID"] = "vQyY8tbjsT6tcG7ZV85N"
os.environ["LOOKERSDK_CLIENT_SECRET"] = "hyPbyWkJXDz8h6tGcYk5Y44G"
os.environ["LOOKERSDK_VERIFY_SSL"] = "false"

print("Initializing SDK...")
sdk = looker_sdk.init40()

print("Switching to dev mode...")
sdk.update_session(looker_sdk.models40.WriteApiSession(workspace_id="dev"))

print("\nRetrieving file content for customer_cdp.model.lkml...")
try:
    file_data = sdk.project_file(
        project_id="antigravity_automatic_poc",
        file_id="customer_cdp.model.lkml"
    )
    
    content = file_data.content or ""
    print(f"\n✅ File retrieved successfully!")
    print(f"Content length: {len(content)} bytes")
    
    if len(content) > 0:
        print(f"\nFirst 300 characters:")
        print(content[:300])
        print("\n✅ SUCCESS: File content is NOT empty! The fix worked!")
    else:
        print("\n❌ FAIL: File content is still empty")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
