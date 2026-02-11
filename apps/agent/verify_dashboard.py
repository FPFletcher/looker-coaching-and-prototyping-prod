import requests
import json

# Toolbox UI API to list tools
TOOLBOX_URL = "http://localhost:5000/ui/js/tools.js" # This is the JS file, not the API. 
# Based on the JS content, we need to know where it fetches from.
# Wait, I saw `loadTools.js` in the output earlier. 

# Let's try to assume we can just check if endpoints exist or if we can hit the running server
# Since the server is running on 5000, we can check health.

def verify_dashboard():
    try:
        resp = requests.get("http://localhost:5000/health") 
        # Toolbox might not have /health, but let's check root
        resp = requests.get("http://localhost:5000/")
        if resp.status_code == 200:
            print("Toolbox is running and accessible.")
        else:
            print(f"Toolbox returned status: {resp.status_code}")
            
    except Exception as e:
        print(f"Failed to connect to Toolbox: {e}")

if __name__ == "__main__":
    verify_dashboard()
