
import os
import looker_sdk
import logging

logging.basicConfig(level=logging.INFO)

def test_exact():
    # Load env vars
    from dotenv import load_dotenv
    load_dotenv("/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/.env")
    
    # Exact logic from create_chart
    # (assuming the values in .env are what create_chart uses)
    
    # Force verify_ssl = true as seen in create_chart code
    os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
    
    # Ensure Base URL has /api/4.0 if that's what create_chart expects?
    # create_chart code:
    # url = f"{url.rstrip('/')}/api/4.0" if "/api/" not in url else url
    # I should simulate this.
    base_url = os.environ.get("LOOKERSDK_BASE_URL", "")
    if "/api/" not in base_url:
        base_url = f"{base_url.rstrip('/')}/api/4.0"
        
    print(f"Using Base URL: {base_url}")
    os.environ["LOOKERSDK_BASE_URL"] = base_url
    
    try:
        print("Initializing SDK 3.1...") # Try 3.1 first? No, create_chart uses 4.0
        # sdk = looker_sdk.init31() 
        # print("SDK 3.1 Me:", sdk.me().display_name)
    except Exception as e:
        print("SDK 3.1 Failed:", e)

    try:
        print("Initializing SDK 4.0...")
        sdk = looker_sdk.init40()
        print("SDK 4.0 Me:", sdk.me().display_name)
        print("SUCCESS")
    except Exception as e:
        print("SDK 4.0 Failed:", e)

if __name__ == "__main__":
    test_exact()
