import urllib.request
import json
import os
import sys

# Load API Key manually since we don't have python-dotenv
def get_api_key():
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('GOOGLE_API_KEY='):
                    return line.split('=')[1].strip()
    except:
        return None

API_KEY = get_api_key()
if not API_KEY:
    print("Error: Could not read GOOGLE_API_KEY from .env")
    sys.exit(1)

# Gemini API Endpoint
# First, let's list models to see what we have access to
list_models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

print(f"Checking access with Key: {API_KEY[:5]}...")

try:
    # 1. List Models
    req = urllib.request.Request(list_models_url)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("✅ API Key working! Available Models:")
        for m in result.get('models', [])[:5]: # Print first 5
            print(f" - {m['name']}")

    # 2. Try Generation with gemini-2.0-flash (Confirmed Available)
    print("\nAttempting generation with 'gemini-2.0-flash'...")
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{
                "text": "You are a Looker Expert. Briefly list 3 key metrics for a SaaS Sales Dashboard."
            }]
        }]
    }

    req = urllib.request.Request(generate_url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("\n✅ Generation Success!")
        print("Response Snippet:")
        print(result['candidates'][0]['content']['parts'][0]['text'])

except urllib.error.HTTPError as e:
    print(f"❌ API Request Failed: {e.code} {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"❌ Error: {e}")
