
import re
import sys
import os

def verify_chat_interface():
    file_path = "apps/web/components/ChatInterface.tsx"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for explore handling
    if '/explore/' not in content or 'embed/explore' not in content:
        print("❌ ChatInterface.tsx does not handle '/explore/' URLs for embedding")
        return False
    
    # Check for dashboard handling
    if '/dashboards/' not in content or 'embed/dashboards' not in content:
        print("❌ ChatInterface.tsx does not handle '/dashboards/' URLs for embedding")
        return False

    print("✅ ChatInterface.tsx logic verified: Handles both Dashboards and Explores")
    return True

if __name__ == "__main__":
    if verify_chat_interface():
        sys.exit(0)
    else:
        sys.exit(1)
