
import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

def debug_auth():
    # Load raw env to avoid any interpolation issues
    from dotenv import load_dotenv
    load_dotenv("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/.env")
    
    base_url = os.environ.get("LOOKERSDK_BASE_URL", "").rstrip('/')
    # If base_url ends in /api/4.0, strip it for root
    if "/api" in base_url:
        root_url = base_url.split("/api")[0]
    else:
        root_url = base_url
        
    client_id = os.environ.get("LOOKERSDK_CLIENT_ID")
    client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET")
    
    print(f"DEBUG: Root URL: {root_url}")
    print(f"DEBUG: Client ID: {client_id[:4]}...{client_id[-4:] if client_id else 'None'}")
    
    endpoints = [
        f"{root_url}/api/3.1/login",  # Promising one (returns 401 instead of 404)
        f"{root_url}/api/4.0/login",
        f"{root_url}/login",
        f"{root_url}:19999/api/3.1/login",
        f"{root_url}:19999/api/4.0/login",
        f"{root_url}:19999/login"
    ]
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "application/json"
    })

    for url in endpoints:
        print(f"\n--- Testing {url} ---")
        
        # Test 1: POST Form Data (Standard)
        try:
            print("  [Attempt 1] Form Data (client_id, client_secret)")
            resp = session.post(url, data={"client_id": client_id, "client_secret": client_secret}, verify=False, timeout=5)
            print(f"  Status: {resp.status_code}")
            print(f"  Body: {resp.text[:200]}")
            if resp.status_code == 200:
                print("  !!! SUCCESS !!!")
                return
        except Exception as e:
            print(f"  Error: {e}")

        # Test 2: POST JSON
        try:
            print("  [Attempt 2] JSON Body")
            resp = session.post(url, json={"client_id": client_id, "client_secret": client_secret}, verify=False, timeout=5)
            print(f"  Status: {resp.status_code}")
            print(f"  Body: {resp.text[:200]}")
            if resp.status_code == 200:
                print("  !!! SUCCESS !!!")
                return
        except Exception as e:
            print(f"  Error: {e}")
            
        # Test 3: UrlEncoded Query Params (Rare but possible)
        try:
            print("  [Attempt 3] Query Params")
            resp = session.post(f"{url}?client_id={client_id}&client_secret={client_secret}", verify=False, timeout=5)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                print("  !!! SUCCESS !!!")
                return
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    debug_auth()
