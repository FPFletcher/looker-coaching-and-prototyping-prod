
import sys
import os
import logging

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

# Add apps/agent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from lookml_context import LookMLContext

def verify_load():
    print("Initializing LookMLContext...")
    context = LookMLContext()
    context.load_from_file()
    
    summary = context.get_summary()
    print("\nBased on .lookml_context.json:")
    print(f"Views: {len(summary['views'])}")
    print(f"Models: {len(summary['models'])}")
    print(f"Explores: {len(summary['explores'])}")
    
    if len(summary['explores']) > 0:
        print("✅ Context loaded successfully.")
    else:
        print("⚠️ Context loaded but is empty (or file missing).")

if __name__ == "__main__":
    verify_load()
