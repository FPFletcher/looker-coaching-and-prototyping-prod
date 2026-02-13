import looker_sdk
import os
import sys

# Mock env to allow init
os.environ["LOOKERSDK_BASE_URL"] = "https://example.com"
os.environ["LOOKERSDK_CLIENT_ID"] = "foo"
os.environ["LOOKERSDK_CLIENT_SECRET"] = "bar"
os.environ["LOOKERSDK_VERIFY_SSL"] = "false"

try:
    sdk = looker_sdk.init40()
    print("SDK initialized")
    print(f"Auth Object Type: {type(sdk.auth)}")
    print("--- Auth Object Dir ---")
    print(dir(sdk.auth))
    
    print("\n--- Transport ---")
    if hasattr(sdk.auth, 'transport'):
        print(f"Transport: {sdk.auth.transport}")
        if hasattr(sdk.auth.transport, 'session'):
             print(f"Session Headers: {sdk.auth.transport.session.headers}")
    
    print("\n--- Testing Token Extraction retrieval ---")
    try:
        if hasattr(sdk.auth, 'get_token'):
            print(f"get_token: {sdk.auth.get_token()}")
    except Exception as e:
        print(f"get_token failed: {e}")

    try:
        if hasattr(sdk.auth, 'retrieve_token'):
             print("Has retrieve_token")
    except:
        pass

except Exception as e:
    print(f"Error: {e}")
