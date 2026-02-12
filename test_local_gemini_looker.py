import requests
import json
import time
import os

API_URL = "http://localhost:8000/api/chat"

# Hardcoded for test simplicity, normally load from env
CREDS = {
    "url": "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app/api/4.0",
    "client_id": "vQyY8tbjsT6tcG7ZV85N",
    "client_secret": "hyPbyWkJXDz8h6tGcYk5Y44G"
}

def test_chat():
    print(f"Testing Chat API at {API_URL}...")
    
    payload = {
        "message": "List the available Looker models you can see.",
        "credentials": CREDS,
        "model": "gemini-2.0-flash"
    }
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=60)
        duration = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            print("Response:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print("Raw Response (Not JSON):")
                print(response.text)
        else:
            print("Error Response:")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat()
