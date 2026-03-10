import requests
import json
import time

URL = "http://localhost:8000/api/explores"
CHAT_URL = "http://localhost:8000/api/chat"

# Credentials for Service Account (User 469 - Admin)
creds = {
    "url": "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
    "client_id": "fSyCPCpCtdb26F8Zwq42",
    "client_secret": "3bs3QFkvRjKFr7cV3cZkyjJH"
}

def test_explores():
    print(f"\n--- Testing /api/explores via Headless Auth ---")
    payload = {"credentials": creds}
    
    try:
        start = time.time()
        res = requests.post(URL, json=payload, timeout=10)
        duration = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            explores = data.get("explores", [])
            print(f"✅ SUCCESS! ({duration:.2f}s)")
            print(f"Found {len(explores)} available explores via Service Account.")
            
            # Highlight 'thelook' vs 'advanced_ecomm'
            thelook_count = len([e for e in explores if e['model'] == 'thelook'])
            adv_count = len([e for e in explores if e['model'] == 'advanced_ecomm'])
            
            print(f" - Explores in 'thelook' model: {thelook_count}")
            print(f" - Explores in 'advanced_ecomm' model: {adv_count}")
            
            if len(explores) > 0:
                print("\nSample Explores:")
                for ex in explores[:3]:
                    print(f" - {ex['label']} (Model: {ex['model']})")
            else:
                print("❌ List is empty! (Check permissions/deployment)")
                
        else:
            print(f"❌ FAILED: {res.status_code}")
            print(f"Response: {res.text}")
            
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")
        print("Is the backend running on port 8000?")

if __name__ == "__main__":
    # Wait for server startup
    time.sleep(2)
    test_explores()
