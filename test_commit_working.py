#!/usr/bin/env python3
"""
Test git commit with correct auth token retrieval
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk
import requests

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("TESTING GIT COMMIT WITH CORRECT AUTH")
print("=" * 80)

try:
    # Get the base URL from SDK
    base_url = sdk.auth.settings.base_url
    
    # Get token the correct way
    token = sdk.auth.token.access_token
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{base_url}/api/4.0/projects/antigravity_automatic_poc_version_2/git/commit"
    
    print(f"URL: {url}")
    print(f"Token (first 20 chars): {token[:20]}...")
    
    response = requests.post(
        url,
        headers=headers,
        json={"message": "Test commit from Python script"},
        verify=False
    )
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code in [200, 201, 204]:
        print(f"\n✅ Commit succeeded!")
    else:
        print(f"\n❌ Commit failed with status {response.status_code}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
