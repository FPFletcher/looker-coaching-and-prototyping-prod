#!/usr/bin/env python3
"""
Verify that LookML file content is properly persisted
"""
import os
import sys
import requests

# Load credentials
base_url = os.environ.get("LOOKERSDK_BASE_URL", "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app")
client_id = os.environ.get("LOOKERSDK_CLIENT_ID", "vQyY8tbjsT6tcG7ZV85N")
client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET", "hyPbyWkJXDz8h6tGcYk5Y44G")

print(f"Testing file content retrieval from {base_url}")

# Login
login_url = f"{base_url.rstrip('/')}/api/4.0/login"
res = requests.post(login_url, data={"client_id": client_id, "client_secret": client_secret}, verify=False)
if res.status_code != 200:
    print(f"Login failed: {res.status_code}")
    sys.exit(1)

token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Switch to dev mode
session_url = f"{base_url.rstrip('/')}/api/4.0/session"
requests.patch(session_url, headers=headers, json={"workspace_id": "dev"}, verify=False)

# Get file content
file_url = f"{base_url.rstrip('/')}/api/4.0/projects/antigravity_automatic_poc/files/file/customer_cdp.model.lkml"
res = requests.get(file_url, headers=headers, verify=False)

if res.status_code == 200:
    file_data = res.json()
    content = file_data.get("content", "")
    print(f"\n✅ File retrieved successfully")
    print(f"Content length: {len(content)} bytes")
    print(f"\nFirst 200 characters:")
    print(content[:200])
    
    if len(content) > 0:
        print("\n✅ SUCCESS: File content is NOT empty!")
    else:
        print("\n❌ FAIL: File content is still empty")
        sys.exit(1)
else:
    print(f"❌ Failed to retrieve file: {res.status_code}")
    print(res.text)
    sys.exit(1)
