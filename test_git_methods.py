#!/usr/bin/env python3
"""
Test Looker SDK git methods to find correct method names
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("TESTING GIT METHODS")
print("=" * 80)

# List all git-related methods
print("\nGit-related methods in SDK:")
git_methods = [m for m in dir(sdk) if 'git' in m.lower()]
for method in git_methods:
    print(f"  - {method}")

# Test git_branch
print("\n" + "=" * 80)
print("Testing git_branch method:")
try:
    branch = sdk.git_branch(project_id="antigravity_automatic_poc_version_2")
    print(f"✅ git_branch works!")
    print(f"   Branch name: {branch.name}")
    print(f"   Can commit: {branch.can_commit}")
    print(f"   Uncommitted changes: {len(branch.uncommitted_changes) if branch.uncommitted_changes else 0}")
    if branch.uncommitted_changes:
        for change in branch.uncommitted_changes[:3]:
            print(f"     - {change.path} ({change.status})")
except Exception as e:
    print(f"❌ git_branch failed: {e}")

# Test commit methods
print("\n" + "=" * 80)
print("Looking for commit methods:")
commit_methods = [m for m in dir(sdk) if 'commit' in m.lower()]
for method in commit_methods:
    print(f"  - {method}")

# Check models for WriteGitBranchCommit
print("\n" + "=" * 80)
print("Checking models40 for git commit models:")
from looker_sdk import models40
git_models = [m for m in dir(models40) if 'git' in m.lower() and 'commit' in m.lower()]
for model in git_models:
    print(f"  - {model}")
