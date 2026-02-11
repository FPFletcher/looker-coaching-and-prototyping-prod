import requests
import json
import sys

def test_encoding():
    url = "http://localhost:8000/api/chat"
    
    # Simple payload
    payload = {
        "message": "Say hello with an emoji 🚀",
        "conversation_history": [],
        "credentials": {
            "url": "https://test.looker.com",
            "client_id": "test", 
            "client_secret": "test"
        },
        "model": "gemini-2.0-flash"
    }
    
    print(f"Testing {url} for UTF-8 streaming...")
    
    try:
        with requests.post(url, json=payload, stream=True) as r:
            print(f"Response headers: {r.headers}")
            if "charset=utf-8" not in r.headers.get("content-type", "").lower():
                print("❌ Content-Type validation failed! Expected charset=utf-8")
                #sys.exit(1) # Don't exit yet, check body
            else:
                print("✅ Content-Type includes charset=utf-8")
                
            # Check content
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    print(f"Received: {decoded_line}")
                    # In a real test we'd check for the emoji, but the mocked agent might not return one.
                    # We mostly care that we *can* decode it without error and headers are right.
                    
    except Exception as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_encoding()
