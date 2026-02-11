#!/usr/bin/env python3
"""
Inspect ProjectFile object structure
"""
import os
import looker_sdk

os.environ["LOOKERSDK_BASE_URL"] = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
os.environ["LOOKERSDK_CLIENT_ID"] = "vQyY8tbjsT6tcG7ZV85N"
os.environ["LOOKERSDK_CLIENT_SECRET"] = "hyPbyWkJXDz8h6tGcYk5Y44G"
os.environ["LOOKERSDK_VERIFY_SSL"] = "false"

sdk = looker_sdk.init40()
sdk.update_session(looker_sdk.models40.WriteApiSession(workspace_id="dev"))

print("Retrieving file...")
file_data = sdk.project_file(
    project_id="antigravity_automatic_poc",
    file_id="customer_cdp.model.lkml"
)

print(f"\nProjectFile object type: {type(file_data)}")
print(f"\nAvailable attributes:")
for attr in dir(file_data):
    if not attr.startswith('_'):
        try:
            value = getattr(file_data, attr)
            if not callable(value):
                print(f"  {attr}: {type(value).__name__}")
                if isinstance(value, str) and len(value) > 0:
                    print(f"    Value preview: {value[:100]}")
        except:
            pass
