#!/usr/bin/env python3
"""
List all projects and find the correct one
"""
import os
from dotenv import load_dotenv
load_dotenv("apps/agent/.env")

import looker_sdk

# Initialize SDK
sdk = looker_sdk.init40()

print("=" * 80)
print("LISTING ALL PROJECTS")
print("=" * 80)

try:
    projects = sdk.all_projects()
    print(f"\n✅ Found {len(projects)} projects:")
    
    for p in projects:
        name = p.name if hasattr(p, 'name') else 'N/A'
        id = p.id if hasattr(p, 'id') else 'N/A'
        uses_git = p.uses_git if hasattr(p, 'uses_git') else False
        
        print(f"\n  Project: {name}")
        print(f"    ID: {id}")
        print(f"    Uses Git: {uses_git}")
        
        # Try to get files for projects that match our search
        if 'antigravity' in name.lower() or 'poc' in name.lower():
            print(f"    🎯 MATCHED PROJECT - trying to list files...")
            try:
                files = sdk.all_project_files(project_id=id)
                print(f"    ✅ Files: {len(files)}")
                for f in files[:5]:
                    print(f"       - {f.path if hasattr(f, 'path') else f}")
            except Exception as e:
                print(f"    ❌ Failed to list files: {str(e)[:100]}")
                
except Exception as e:
    print(f"❌ Failed to list projects: {e}")

print("\n" + "=" * 80)
