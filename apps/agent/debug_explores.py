
import os
import looker_sdk
from looker_sdk import models40
import logging
import json
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

def debug_explores():
    logger.info("--- Starting Explore Debugger ---")
    
    # Init SDK
    try:
        sdk = looker_sdk.init40()
        logger.info("✅ SDK Initialized")
    except Exception as e:
        logger.error(f"Failed to init SDK: {e}")
        return

    # 1. Verify User & Workspace
    try:
        me = sdk.me()
        logger.info(f"User ID: {me.id}, Email: {me.email}, Roles: {me.role_ids}")
        
        session = sdk.session()
        logger.info(f"Current Workspace: {session.workspace_id}")
        
        # Check permissions
        # We can't easily list all permissions, but role '2' is usually Admin.
        
    except Exception as e:
        logger.error(f"User check failed: {e}")

    # 2. Inspect 'advanced_ecomm' Model specifically
    target_model = "advanced_ecomm"
    logger.info(f"Inspecting Model: {target_model}")
    
    try:
        # Get full model details
        model = sdk.lookml_model(lookml_model_name=target_model)
        logger.info(f"Model Found: {model.name} (Project: {model.project_name})")
        logger.info(f"Allowed via: {model.allowed_db_connection_names}")
        
        # Check Explores
        if model.explores:
            logger.info(f"Explores Count: {len(model.explores)}")
            for e in model.explores:
                logger.info(f" - Explore: {e.name} (Hidden: {e.hidden})")
        else:
            logger.warning("❌ Model has NO Explores list in the response object.")
            
            # Why?
            # 1. Project hasn't been deployed to Production?
            # 2. Explores are hidden?
            
    except Exception as e:
        logger.warning(f"Failed to get specific model '{target_model}': {e}")
        
    # 3. List ALL models to see what is visible
    try:
        all_models = sdk.all_lookml_models(fields="name,project_name,has_content,explores")
        logger.info(f"Total Models Visible: {len(all_models)}")
        for m in all_models:
            explores_count = len(m.explores) if m.explores else 0
            logger.info(f" - Model: {m.name} [Project: {m.project_name}] Explores: {explores_count}")
            
    except Exception as e:
        logger.error(f"List all models failed: {e}")

    # 4. Attempt to switch to Dev Mode (if applicable) and check again
    # Service Accounts usually default to Production.
    try:
        logger.info("Attempting to switch to 'dev' workspace...")
        sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
        session = sdk.session()
        logger.info(f"New Workspace: {session.workspace_id}")
        
        # Check Model again in Dev
        model_dev = sdk.lookml_model(lookml_model_name=target_model)
        dev_explores = len(model_dev.explores) if model_dev.explores else 0
        logger.info(f"Dev Mode Explores Count: {dev_explores}")
        
    except Exception as e:
        logger.warning(f"Could not switch to Dev mode (Expected for SA): {e}")

if __name__ == "__main__":
    debug_explores()
