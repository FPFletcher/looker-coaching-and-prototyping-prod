import os
import sys
import looker_sdk
from looker_sdk import models40
import logging
from dotenv import load_dotenv

# Load env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LookerAuthTest")

def test_connection():
    logger.info("--- Starting Looker Connection Test ---")
    
    # 1. Check Environment Variables
    base_url = os.environ.get("LOOKERSDK_BASE_URL")
    client_id = os.environ.get("LOOKERSDK_CLIENT_ID")
    client_secret = os.environ.get("LOOKERSDK_CLIENT_SECRET")
    
    logger.info(f"Checking configuration:")
    logger.info(f"  URL: {base_url}")
    logger.info(f"  Client ID: {client_id[:4]}...{client_id[-4:] if client_id else 'None'}")
    logger.info(f"  Client Secret: {'*' * 5} (Present: {bool(client_secret)})")

    if not all([base_url, client_id, client_secret]):
        logger.error("❌ FAILURE: Missing environment variables.")
        return

    # 2. Initialize SDK
    try:
        os.environ["LOOKERSDK_VERIFY_SSL"] = "false"
        sdk = looker_sdk.init40()
        logger.info("✅ SDK Initialized (4.0)")
    except Exception as e:
        logger.error(f"❌ SDK Initialization Failed: {e}")
        return

    # 3. Test Authentication (Who am I?)
    try:
        me = sdk.me()
        logger.info(f"✅ Authentication SUCCESS!")
        logger.info(f"  User ID: {me.id}")
        logger.info(f"  Name: {me.display_name}")
        logger.info(f"  Email: {me.email}")
        logger.info(f"  Roles: {me.role_ids}")
        logger.info(f"  Personal Folder ID: {me.personal_folder_id}")
    except Exception as e:
        logger.error(f"❌ Authentication FAILED: {e}")
        logger.error("  -> This confirms credentials are invalid or rejected by API.")
        return

    # 4. Test Permissions / Access
    try:
        # Try fetching dashboards (SDK 4.0 all_dashboards might not take limit arg in python sdk)
        dashboards = sdk.all_dashboards()
        logger.info(f"✅ Dashboard Access: Success. Found {len(dashboards)} dashboards.")
        if dashboards:
            # Show first 3
            for d in dashboards[:3]:
                logger.info(f"    - {d.title} (ID: {d.id}, Folder: {d.folder.name if d.folder else 'Unknown'})")
            
        # Try fetching looks
        looks = sdk.all_looks()
        logger.info(f"✅ Look Access: Success. Found {len(looks)} looks.")
        
        # Try fetching models (Critical for Explore Dropdown)
        models = sdk.all_lookml_models(fields="name,label,project_name,explores")
        logger.info(f"✅ Model Access: Success. Found {len(models)} models.")
        if models:
            for m in models[:3]:
                 explores_count = len(m.explores) if m.explores else 0
                 logger.info(f"    - Model: {m.name} ({m.label}) - Explores: {explores_count}")
        else:
            logger.warning("⚠️ No Models found! The Explore Dropdown will be empty.")
            logger.warning("   Check if these credentials have access to any Models/Projects.")

        # Try fetching users (Admin check)
        users = sdk.all_users(limit=3)
        logger.info(f"✅ User Access: Success. Found users.")

    except Exception as e:
        logger.warning(f"⚠️ Access Check Partial Failure: {e}")

    logger.info("--- Test Complete ---")
    logger.info("CONCLUSION:")
    logger.info("If Authentication was SUCCESS, the Backend API is working.")
    logger.info("Visual Embedding requires a separate mechanism (Signed Embedding) or standard session.")

if __name__ == "__main__":
    test_connection()
