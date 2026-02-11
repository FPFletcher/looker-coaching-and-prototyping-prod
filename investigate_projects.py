#!/usr/bin/env python3
"""
Investigate project Git configuration and attempt GitHub commit
"""
import sys
import os
from dotenv import load_dotenv
import looker_sdk

load_dotenv("apps/agent/.env")

def init_sdk():
    sdk = looker_sdk.init40()
    return sdk

def investigate_projects():
    sdk = init_sdk()
    
    print("=" * 80)
    print("INVESTIGATING PROJECT CONFIGURATIONS")
    print("=" * 80)
    
    for project_id in ["antigravity_automatic_poc_version_2", "antigravity_automatic_poc_version_3"]:
        print(f"\n{'='*80}")
        print(f"PROJECT: {project_id}")
        print(f"{'='*80}")
        
        try:
            # Get project details
            project = sdk.project(project_id)
            print(f"\nProject Details:")
            print(f"  Name: {project.name}")
            print(f"  ID: {project.id}")
            print(f"  Git Service Name: {project.git_service_name}")
            print(f"  Git Remote URL: {project.git_remote_url}")
            print(f"  Git Username: {project.git_username}")
            print(f"  Deploy Secret: {'***' if project.deploy_secret else 'None'}")
            print(f"  Pull Request Mode: {project.pull_request_mode}")
            print(f"  Validation Required: {project.validation_required}")
            print(f"  Allow Warnings: {project.allow_warnings}")
            print(f"  Is Example: {project.is_example}")
            
            # Try to get Git connection status
            try:
                git_branch = sdk.git_branch(project_id)
                print(f"\nGit Branch Info:")
                print(f"  Name: {git_branch.name}")
                print(f"  Remote: {git_branch.remote}")
                print(f"  Remote Name: {git_branch.remote_name}")
                print(f"  Ahead Count: {git_branch.ahead_count}")
                print(f"  Behind Count: {git_branch.behind_count}")
            except Exception as e:
                print(f"\n❌ Git Branch Error: {e}")
            
            # Try to get manifest
            try:
                manifest = sdk.manifest(project_id)
                print(f"\nManifest:")
                print(f"  Name: {manifest.name}")
                print(f"  Models: {len(manifest.models or [])}")
            except Exception as e:
                print(f"\n❌ Manifest Error: {e}")
                
        except Exception as e:
            print(f"\n❌ Project Error: {e}")
    
    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    investigate_projects()
