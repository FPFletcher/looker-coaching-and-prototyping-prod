#!/usr/bin/env python3
"""
Test with the working project name from earlier tests
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk

# Initialize SDK
sdk = looker_sdk.init40()

# Use the project that worked in earlier tests
project_id = "antigravity_automatic_poc"

print("=" * 80)
print(f"TESTING FILE ACCESS FOR: {project_id}")
print("=" * 80)

# Test 1: all_project_files
print("\n1. Testing all_project_files():")
try:
    files = sdk.all_project_files(project_id=project_id)
    print(f"✅ Found {len(files)} files:")
    for f in files:
        path = f.path if hasattr(f, 'path') else str(f)
        print(f"   - {path}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Get specific file content
print("\n2. Testing project_file() for specific files:")
test_files = ["customer_360.model.lkml", "users.view.lkml", "manifest.lkml"]
for file_path in test_files:
    try:
        file_content = sdk.project_file(
            project_id=project_id,
            file_id=file_path
        )
        print(f"\n✅ Retrieved: {file_path}")
        if hasattr(file_content, 'content') and file_content.content:
            print(f"   Content ({len(file_content.content)} chars):")
            print(f"   {file_content.content[:300]}")
        else:
            print(f"   No content attribute")
    except Exception as e:
        print(f"❌ {file_path}: {str(e)[:100]}")

# Test 3: git_branch
print("\n3. Testing git_branch():")
try:
    branch = sdk.git_branch(project_id=project_id)
    print(f"✅ Branch: {branch.name if hasattr(branch, 'name') else 'N/A'}")
    
    if hasattr(branch, 'uncommitted_changes') and branch.uncommitted_changes:
        print(f"   Uncommitted files ({len(branch.uncommitted_changes)}):")
        for change in branch.uncommitted_changes:
            print(f"     - {change.path if hasattr(change, 'path') else change}")
    else:
        print(f"   No uncommitted changes")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "=" * 80)
