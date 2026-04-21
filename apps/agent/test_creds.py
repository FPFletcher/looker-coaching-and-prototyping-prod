import json
from google.oauth2 import service_account

try:
    with open('vertex-sa-key.json', 'r') as f:
        info = json.load(f)
    
    creds = service_account.Credentials.from_service_account_info(info)
    print("SUCCESS: Credentials loaded successfully!")
except Exception as e:
    print("FAILED:", e)
    import traceback
    traceback.print_exc()
