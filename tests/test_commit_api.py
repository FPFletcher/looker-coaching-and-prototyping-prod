#!/usr/bin/env python3
"""
Inspect WriteGitBranch model to find correct attributes
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk
from looker_sdk import models40
import inspect

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("INSPECTING WriteGitBranch MODEL")
print("=" * 80)

# Get the actual __init__ signature
print("\nWriteGitBranch.__init__ signature:")
try:
    sig = inspect.signature(models40.WriteGitBranch.__init__)
    print(f"  {sig}")
except Exception as e:
    print(f"  Error: {e}")

# Try to create an instance and see what happens
print("\nTrying to create WriteGitBranch instance:")
try:
    branch = models40.WriteGitBranch()
    print(f"  Created: {branch}")
    print(f"  Type: {type(branch)}")
    print(f"  Dict: {dict(branch)}")
except Exception as e:
    print(f"  Error: {e}")

# Search for commit-related models
print("\n" + "=" * 80)
print("Searching for commit-related models in models40:")
commit_models = [m for m in dir(models40) if 'commit' in m.lower()]
for model in commit_models:
    print(f"  - {model}")

# Check if there's a REST API endpoint we should use directly
print("\n" + "=" * 80)
print("Checking Looker API documentation pattern:")
print("  POST /projects/{project_id}/git/commit")
print("  This might need to be called via raw HTTP")

# Test with raw HTTP request
print("\n" + "=" * 80)
print("Testing raw HTTP commit:")
try:
    import requests
    
    # Get token
    token = sdk.auth.token.access_token
    headers = {"Authorization": f"Bearer {token}"}
    
    url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app/api/4.0/projects/antigravity_automatic_poc_version_2/git/commit"
    
    response = requests.post(
        url,
        headers=headers,
        json={"message": "Test commit via raw API"},
        verify=False
    )
    
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:500]}")
    
except Exception as e:
    print(f"  Error: {e}")
