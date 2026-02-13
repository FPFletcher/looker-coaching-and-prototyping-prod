#!/usr/bin/env python3
"""
Test different methods to access LookML files in the project
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk

# Initialize SDK
sdk = looker_sdk.init40()

project_id = "antigravity_automatic_poc_version_2"

print("=" * 80)
print("TESTING METHODS TO ACCESS LOOKML FILES")
print("=" * 80)

# Method 1: all_project_files
print("\n1. Testing all_project_files():")
try:
    files = sdk.all_project_files(project_id=project_id)
    print(f"✅ Found {len(files)} files")
    for f in files[:10]:
        print(f"   - {f.path if hasattr(f, 'path') else f}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Method 2: project_file (get specific file)
print("\n2. Testing project_file() for a specific file:")
try:
    # Try to get a known file
    file_content = sdk.project_file(
        project_id=project_id,
        file_id="customer_360.model.lkml"
    )
    print(f"✅ Retrieved file!")
    print(f"   Path: {file_content.path if hasattr(file_content, 'path') else 'N/A'}")
    print(f"   Content length: {len(file_content.content) if hasattr(file_content, 'content') else 0}")
    if hasattr(file_content, 'content') and file_content.content:
        print(f"   First 200 chars: {file_content.content[:200]}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Method 3: git_branch to see uncommitted files
print("\n3. Testing git_branch() to see uncommitted changes:")
try:
    branch = sdk.git_branch(project_id=project_id)
    print(f"✅ Branch: {branch.name if hasattr(branch, 'name') else 'N/A'}")
    
    if hasattr(branch, 'uncommitted_changes') and branch.uncommitted_changes:
        print(f"   Uncommitted files: {len(branch.uncommitted_changes)}")
        for change in branch.uncommitted_changes[:10]:
            print(f"     - {change.path if hasattr(change, 'path') else change} ({change.status if hasattr(change, 'status') else 'unknown'})")
    else:
        print(f"   No uncommitted changes")
except Exception as e:
    print(f"❌ Failed: {e}")

# Method 4: Check project workspace files
print("\n4. Testing project_workspace():")
try:
    workspace = sdk.project_workspace(project_id=project_id)
    print(f"✅ Workspace info:")
    print(f"   Workspace ID: {workspace.workspace_id if hasattr(workspace, 'workspace_id') else 'N/A'}")
    print(f"   Projects: {workspace.projects if hasattr(workspace, 'projects') else 'N/A'}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Method 5: List all files with fields parameter
print("\n5. Testing all_project_files() with fields:")
try:
    files = sdk.all_project_files(
        project_id=project_id,
        fields="path,type,git_status"
    )
    print(f"✅ Found {len(files)} files with details")
    for f in files[:10]:
        path = f.path if hasattr(f, 'path') else 'N/A'
        git_status = f.git_status if hasattr(f, 'git_status') else 'N/A'
        print(f"   - {path} (git_status: {git_status})")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "=" * 80)
