#!/usr/bin/env python3
"""
Test update_git_branch for committing changes
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk
from looker_sdk import models40

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("TESTING update_git_branch FOR COMMITTING")
print("=" * 80)

# Check the signature of update_git_branch
import inspect
print("\nupdate_git_branch signature:")
sig = inspect.signature(sdk.update_git_branch)
print(f"  {sig}")

# Check WriteGitBranch model
print("\nWriteGitBranch model attributes:")
write_git_attrs = [attr for attr in dir(models40.WriteGitBranch) if not attr.startswith('_')]
for attr in write_git_attrs[:20]:  # Show first 20
    print(f"  - {attr}")

# Try to commit using update_git_branch
print("\n" + "=" * 80)
print("Attempting to commit using update_git_branch:")
try:
    result = sdk.update_git_branch(
        project_id="antigravity_automatic_poc_version_2",
        body=models40.WriteGitBranch(
            name="master",
            commit_message="Test commit from SDK"
        )
    )
    print(f"✅ Commit succeeded!")
    print(f"   Result: {result}")
except Exception as e:
    print(f"❌ Commit failed: {e}")

# Alternative: Check if there's a deploy method
print("\n" + "=" * 80)
print("Looking for deploy methods:")
deploy_methods = [m for m in dir(sdk) if 'deploy' in m.lower()]
for method in deploy_methods:
    print(f"  - {method}")
