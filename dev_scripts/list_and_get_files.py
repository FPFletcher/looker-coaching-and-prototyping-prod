#!/usr/bin/env python3
"""
List all files in the project to verify they exist
"""
import os
import sys
import requests

base_url = os.environ.get("LOOKERSDK_BASE_URL", "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app")
client_id = os.environ.get("LOOKERSDK_CLIENT_ID", "vQyY8tbjsT6tcG7ZV85N")
client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET", "hyPbyWkJXDz8h6tGcYk5Y44G")

print(f"Listing files in antigravity_automatic_poc")

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

# List files
files_url = f"{base_url.rstrip('/')}/api/4.0/projects/antigravity_automatic_poc/files"
res = requests.get(files_url, headers=headers, verify=False)

if res.status_code == 200:
    files = res.json()
    print(f"\n✅ Found {len(files)} files:")
    for f in files:
        print(f"  - {f.get('path')} ({f.get('type')}) - ID: {f.get('id')}")
        
    # Try to get content of first file
    if files:
        first_file = files[0]
        file_id = first_file.get('id')
        print(f"\nTrying to retrieve content of: {file_id}")
        
        # Try different endpoint formats
        endpoints = [
            f"{base_url.rstrip('/')}/api/4.0/projects/antigravity_automatic_poc/files/file/{file_id}",
            f"{base_url.rstrip('/')}/api/4.0/projects/antigravity_automatic_poc/files/{file_id}",
            f"{base_url.rstrip('/')}/api/4.0/project_files/antigravity_automatic_poc/{file_id}",
        ]
        
        for endpoint in endpoints:
            print(f"\nTrying: {endpoint}")
            res = requests.get(endpoint, headers=headers, verify=False)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                content = data.get('content', '')
                print(f"✅ SUCCESS! Content length: {len(content)} bytes")
                if content:
                    print(f"First 200 chars: {content[:200]}")
                break
else:
    print(f"❌ Failed to list files: {res.status_code}")
    print(res.text)
