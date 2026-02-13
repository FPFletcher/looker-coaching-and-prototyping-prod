
import requests
import os
import json

def debug_session():
    base_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print(f"Target: {base_url}")
    
    # Login
    login_url = f"{base_url}/api/4.0/login"
    res = requests.post(login_url, data={"client_id": client_id, "client_secret": client_secret}, verify=False)
    if res.status_code != 200:
        print(f"Login Failed: {res.status_code} {res.text}")
        return
        
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login Success.")
    
    # 1. Who am I?
    print("\n--- User Info ---")
    res = requests.get(f"{base_url}/api/4.0/user", headers=headers, verify=False)
    user = res.json()
    print(f"ID: {user.get('id')}")
    print(f"Name: {user.get('display_name')}")
    print(f"Role IDs: {user.get('role_ids')}")
    
    # 2. Check Permissions
    print("\n--- Roles ---")
    for role_id in user.get('role_ids', []):
        r_res = requests.get(f"{base_url}/api/4.0/roles/{role_id}", headers=headers, verify=False)
        role = r_res.json()
        print(f"Role {role_id}: {role.get('name')}")
        # print(f"Permissions: {role.get('permission_set', {}).get('permissions', [])}")

    # 3. Current Session
    print("\n--- Session ---")
    res = requests.get(f"{base_url}/api/4.0/session", headers=headers, verify=False)
    print(f"Current Workspace: {res.json().get('workspace_id')}")
    
    # 4. Try Switch
    print("\n--- Try Switch to Dev ---")
    res = requests.patch(f"{base_url}/api/4.0/session", headers=headers, json={"workspace_id": "dev"}, verify=False)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    debug_session()
