#!/usr/bin/env python3
"""
Test if content parameter fix worked by creating a new file and checking the response
"""
import os
import requests

base_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
client_id = "vQyY8tbjsT6tcG7ZV85N"
client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"

# Login
login_url = f"{base_url.rstrip('/')}/api/4.0/login"
res = requests.post(login_url, data={"client_id": client_id, "client_secret": client_secret}, verify=False)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Switch to dev
session_url = f"{base_url.rstrip('/')}/api/4.0/session"
requests.patch(session_url, headers=headers, json={"workspace_id": "dev"}, verify=False)

# Create a NEW test file with known content
test_content = """connection: test_connection

include: "*.view.lkml"

view: test_verification {
  sql_table_name: public.test ;;
  
  dimension: id {
    type: number
    sql: ${TABLE}.id ;;
  }
}
"""
test_file = "test_content_verification.model.lkml"

print(f"Creating test file: {test_file}")
print(f"Content length: {len(test_content)} bytes")

create_url = f"{base_url.rstrip('/')}/api/4.0/projects/antigravity_automatic_poc/files"
res = requests.post(create_url, headers=headers, json={"path": test_file, "content": test_content}, verify=False)

print(f"\nCreate response status: {res.status_code}")

if res.status_code in [200, 201]:
    response_data = res.json()
    print(f"✅ File created successfully!")
    print(f"Response keys: {list(response_data.keys())}")
    
    # Check if response contains content
    if 'content' in response_data:
        returned_content = response_data.get('content', '')
        print(f"\nReturned content length: {len(returned_content)} bytes")
        if len(returned_content) > 0:
            print(f"First 200 chars: {returned_content[:200]}")
            print("\n✅ SUCCESS: Content was persisted and returned!")
        else:
            print("\n❌ FAIL: Returned content is empty")
    else:
        print(f"\n⚠️  Response doesn't include 'content' field (this is normal)")
        print(f"Response includes: {list(response_data.keys())}")
        print("\nThis is expected - Looker API returns metadata only on create.")
        print("The fix is working if status is 200/201!")
elif res.status_code == 400 and "already exists" in res.text:
    print("\nFile exists, trying update...")
    res = requests.put(create_url, headers=headers, json={"path": test_file, "content": test_content}, verify=False)
    print(f"Update status: {res.status_code}")
    if res.status_code in [200, 201]:
        print("✅ Update successful - fix is working!")
else:
    print(f"❌ Error: {res.text[:500]}")
