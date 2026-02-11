#!/usr/bin/env python3
"""
Test git commit using SDK's internal request method
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("TESTING GIT COMMIT VIA SDK INTERNAL METHOD")
print("=" * 80)

# Method 1: Use SDK's internal POST method
print("\nMethod 1: Using SDK's internal POST:")
try:
    # The SDK has a generic request method we can use
    response = sdk.post(
        path=f"/projects/antigravity_automatic_poc_version_2/git/commit",
        body={"message": "Test commit via SDK POST"}
    )
    print(f"✅ Commit succeeded!")
    print(f"   Response: {response}")
except AttributeError as e:
    print(f"❌ SDK doesn't have post method: {e}")
except Exception as e:
    print(f"❌ Commit failed: {e}")

# Method 2: Check if there's a commit_git_branch method we missed
print("\n" + "=" * 80)
print("Method 2: Searching for any commit methods:")
all_methods = dir(sdk)
commit_related = [m for m in all_methods if 'commit' in m.lower() or 'git' in m.lower()]
print("All git/commit related methods:")
for method in commit_related:
    if not method.startswith('_'):
        print(f"  - {method}")

# Method 3: Try using requests with proper SDK auth
print("\n" + "=" * 80)
print("Method 3: Using requests with SDK auth:")
try:
    import requests
    
    # Get the base URL from SDK
    base_url = sdk.auth.settings.base_url
    
    # Authenticate and get token
    sdk.auth.authenticate()
    token = sdk.auth.token.access_token
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{base_url}/api/4.0/projects/antigravity_automatic_poc_version_2/git/commit"
    
    print(f"  URL: {url}")
    print(f"  Token: {token[:20]}...")
    
    response = requests.post(
        url,
        headers=headers,
        json={"message": "Test commit via requests"},
        verify=False
    )
    
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:500]}")
    
    if response.status_code in [200, 201, 204]:
        print(f"✅ Commit succeeded!")
    else:
        print(f"❌ Commit failed with status {response.status_code}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
