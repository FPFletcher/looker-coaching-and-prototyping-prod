import looker_sdk
import os

os.environ["LOOKERSDK_BASE_URL"] = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app" # No api/4.0 for now, SDK appends it? Or maybe with?
os.environ["LOOKERSDK_CLIENT_ID"] = "vQyY8tbjsT6tcG7ZV85N"
os.environ["LOOKERSDK_CLIENT_SECRET"] = "hyPbyWkJXDz8h6tGcYk5Y44G"
os.environ["LOOKERSDK_VERIFY_SSL"] = "true"

def test_sdk():
    print(f"Testing Looker SDK...")
    
    # Try with plain URL
    try:
        sdk = looker_sdk.init40()
        me = sdk.me()
        print(f"SDK Me: {me.display_name}")
    except Exception as e:
        print(f"SDK Init Error (plain URL): {e}")
        
    # Try with /api/4.0
    os.environ["LOOKERSDK_BASE_URL"] = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app/api/4.0" # Standard SDK format requires API path?
    try:
        print("Retrying SDK with /api/4.0 suffix...")
        sdk = looker_sdk.init40()
        me = sdk.me()
        print(f"SDK Me (suffix): {me.display_name}")
    except Exception as e:
        print(f"SDK Init Error (suffix): {e}")

if __name__ == "__main__":
    test_sdk()
