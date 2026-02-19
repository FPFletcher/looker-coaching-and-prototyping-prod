
import logging
import sys
import os

# Add parent directory to path to define modules if needed, though we primarily need looker_sdk
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import looker_sdk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_get_models():
    print("--- Starting Debug: get_models ---")
    try:
        # Load credentials from env arguments if present
        if len(sys.argv) > 3:
            os.environ["LOOKERSDK_BASE_URL"] = sys.argv[1]
            os.environ["LOOKERSDK_CLIENT_ID"] = sys.argv[2]
            os.environ["LOOKERSDK_CLIENT_SECRET"] = sys.argv[3]
            os.environ["LOOKERSDK_VERIFY_SSL"] = "false" # Match main.py
            print(f"✅ Credentials loaded for: {sys.argv[1]}")
        
        # Initialize SDK
        sdk = looker_sdk.init40()
        print("✅ SDK Initialized")
        
        me = sdk.me()
        print(f"✅ Authenticated as: {me.display_name} (ID: {me.id})")
        
        print("\n--- TEST 1: all_lookml_models() ---")
        try:
            lookml_models = sdk.all_lookml_models(fields="name,project_name,explores")
            print(f"Result count: {len(lookml_models)}")
            for m in lookml_models:
                print(f" - Model: {m.name} | Project: {m.project_name} | Explores: {len(m.explores or [])}")
        except Exception as e:
            print(f"❌ all_lookml_models failed: {e}")

        print("\n--- TEST 2: all_lookml_models() raw (no fields) ---")
        try:
            lookml_models_raw = sdk.all_lookml_models()
            print(f"Result count: {len(lookml_models_raw)}")
        except Exception as e:
            print(f"❌ all_lookml_models raw failed: {e}")
            
    except Exception as e:
        print(f"❌ critical failure: {e}")

if __name__ == "__main__":
    debug_get_models()
