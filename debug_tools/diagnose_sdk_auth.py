
import os
import sys
import logging
import requests
from looker_sdk import init40

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose():
    # Load env vars from .env for simulation
    from dotenv import load_dotenv
    load_dotenv("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/.env")
    
    base_url = os.environ.get("LOOKERSDK_BASE_URL")
    client_id = os.environ.get("LOOKERSDK_CLIENT_ID")
    client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET")
    
    print(f"Current Base URL: {base_url}")
    
    # 1. Probe Login Endpoints
    print("\n--- Probing Login Endpoints ---")
    candidates = [
        f"{base_url}/login",
        f"{base_url}/api/4.0/login",
        f"{base_url.replace('/api/4.0', '')}/login",
        f"{base_url.replace('/api/4.0', '')}/api/4.0/login",
        f"{base_url.replace('/api/4.0', '')}:19999/api/4.0/login"
    ]
    
    for url in candidates:
        try:
            print(f"Trying: {url}")
            res = requests.post(url, data={"client_id": client_id, "client_secret": client_secret})
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print(">>> SUCCESS! Found login endpoint.")
                try:
                    print("Token received:", res.json().get("access_token")[:5] + "...")
                except:
                    pass
        except Exception as e:
            print(f"Failed: {e}")

    # 2. Inspect SDK Write Methods
    print("\n--- Inspecting SDK Write Methods ---")
    try:
        sdk = init40()
        print("SDK Initialized.")
        
        print("\nMethods starting with 'create':")
        methods = [m for m in dir(sdk) if m.startswith('create')]
        for m in methods:
            print(f" - {m}")
            
        print("\nMethods starting with 'update':")
        methods = [m for m in dir(sdk) if m.startswith('update')]
        for m in methods:
            print(f" - {m}")

    except Exception as e:
        print(f"SDK Init Failed: {e}")
        
    # 3. Brute Force Token (Aggressive)
    print("\n--- Brute Force Token Check (Aggressive) ---")
    
    # Clean base URL to root
    if "/api" in base_url:
        root_url = base_url.split("/api")[0]
    else:
        root_url = base_url.rstrip("/")

    targets = [
        f"{root_url}/login",
        f"{root_url}/api/4.0/login",
        f"{root_url}/api/3.1/login",
        f"{base_url}/login" # Original configured
    ]

    for url in targets:
        print(f"\nTarget: {url}")
        
        # Try Form Data
        try:
            print("  Trying Form Data...")
            res = requests.post(url, data={"client_id": client_id, "client_secret": client_secret}, verify=False)
            print(f"  Status: {res.status_code}")
            if res.status_code == 200:
                print(f"  >>> SUCCESS (Form)! Token: {res.json().get('access_token')[:10]}...")
                return # Found it
            else:
                print(f"  Response: {res.text[:100]}")
        except Exception as e:
            print(f"  Error: {e}")

        # Try JSON
        try:
            print("  Trying JSON Data...")
            res = requests.post(url, json={"client_id": client_id, "client_secret": client_secret}, verify=False)
            print(f"  Status: {res.status_code}")
            if res.status_code == 200:
                print(f"  >>> SUCCESS (JSON)! Token: {res.json().get('access_token')[:10]}...")
                return # Found it
        except Exception as e:
             pass

if __name__ == "__main__":
    diagnose()
