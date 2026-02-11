
import os
import sys
import logging
import requests
import looker_sdk
from looker_sdk import methods40, models40

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LookerDiag")

def diagnose():
    # Load .env explicitly to be sure
    from dotenv import load_dotenv
    env_path = "/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/.env"
    load_dotenv(env_path)
    
    base_url_raw = os.environ.get("LOOKERSDK_BASE_URL", "").strip().rstrip('/')
    client_id = os.environ.get("LOOKERSDK_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET", "").strip()
    
    if not all([base_url_raw, client_id, client_secret]):
        logger.error("Missing credentials in .env")
        return

    logger.info(f"Targeting Base URL: {base_url_raw}")
    logger.info(f"Client ID: {client_id[:4]}...{client_id[-4:]}")

    # Generate URL candidates
    # Common Looker patterns:
    # - https://instance.looker.com
    # - https://instance.looker.com:19999 (API port)
    # - https://instance.looker.com/api/3.1
    # - https://instance.looker.com/api/4.0
    
    # Clean root (remove /api/...)
    if "/api" in base_url_raw:
        root_url = base_url_raw.split("/api")[0]
    else:
        root_url = base_url_raw
        
    url_variations = [
        root_url,
        f"{root_url}:19999",
        f"{root_url}/api/3.1",
        f"{root_url}/api/4.0",
        f"{root_url}:19999/api/3.1",
        f"{root_url}:19999/api/4.0"
    ]
    # Deduplicate
    url_variations = list(dict.fromkeys(url_variations))
    
    success_found = False

    print("\n=== STARTING DIAGNOSTIC ===\n")

    # 1. Test SDK Initialization (Only 4.0)
    print("--- 1. SDK 4.0 Initialization Tests ---")
    for ssl_verify in ["true", "false"]:
        # Only testing 40 since 31 is missing in this SDK
        version = 40
        init_method = looker_sdk.init40
        for url in url_variations:
            try:
                # Setup Env
                os.environ["LOOKERSDK_BASE_URL"] = url
                os.environ["LOOKERSDK_VERIFY_SSL"] = ssl_verify
                os.environ["LOOKERSDK_TIMEOUT"] = "5"
                
                print(f"Testing SDK {version} | URL: {url} | SSL: {ssl_verify} ... ", end="")
                
                sdk = init_method()
                me = sdk.me()
                print(f"SUCCESS! (User: {me.display_name})")
                success_found = True
                return 
                
            except Exception as e:
                pass # print(f"Fail")

    # 2. Test Raw HTTP Login
    print("\n--- 2. Raw HTTP Login Tests ---")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    })
    
    # Payloads
    payload_variants = [
        ("Form (Snake)", {"client_id": client_id, "client_secret": client_secret}, "data"),
        ("JSON (Snake)", {"client_id": client_id, "client_secret": client_secret}, "json"),
        ("Form (Camel)", {"clientId": client_id, "clientSecret": client_secret}, "data"),
        ("JSON (Camel)", {"clientId": client_id, "clientSecret": client_secret}, "json")
    ]
    
    for url in url_variations:
        # Construct Login Endpoint candidates
        base_clean = url.rstrip('/')
        login_endpoints = [
            f"{base_clean}/login",
            f"{base_clean}/api/3.0/login",
            f"{base_clean}/api/3.1/login",
            f"{base_clean}/api/4.0/login"
        ]
            
        for login_url in login_endpoints:
            if not login_url.startswith("http"): continue
            
            for label, payload, method in payload_variants:
                try:
                    # print(f"Testing {login_url} [{label}] ... ", end="")
                    if method == "data":
                        res = session.post(login_url, data=payload, verify=False, timeout=5)
                    else:
                        res = session.post(login_url, json=payload, verify=False, timeout=5)
                    
                    if res.status_code == 200:
                        print(f"\n!!!! RAW AUTH SUCCESS !!!!\nURL: {login_url}\nMethod: {label}")
                        print(f"Token: {res.json().get('access_token')[:10]}...")
                        success_found = True
                        return
                    elif res.status_code not in [404, 401, 403]:
                        print(f"{login_url} [{label}] -> {res.status_code}")
                        
                except Exception as e:
                    pass

    print("\n=== DIAGNOSTIC COMPLETE ===")
    if not success_found:
        print("❌ NO WORKING CONFIGURATION FOUND.")
    else:
        print("✅ AT LEAST ONE CONFIGURATION WORKED.")

    print("\n=== DIAGNOSTIC COMPLETE ===")
    if not success_found:
        print("❌ NO WORKING CONFIGURATION FOUND.")
    else:
        print("✅ AT LEAST ONE CONFIGURATION WORKED.")

if __name__ == "__main__":
    diagnose()
