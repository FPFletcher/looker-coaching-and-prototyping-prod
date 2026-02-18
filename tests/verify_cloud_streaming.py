import requests
import json
import os

# Backend URL (from previous deployment output)
BACKEND_URL = "https://looker-mcp-agent-backend-734857282249.europe-west1.run.app/api/chat"

# Dummy credentials (the agent might fail to connect to Looker, but it should still stream the attempt)
payload = {
    "message": "Hello, are you there?",
    "conversation_history": [],
    "credentials": {
        "url": "https://example.looker.com",
        "client_id": "dummy",
        "client_secret": "dummy"
    },
    "model": "claude-3-5-sonnet-20240620"
}

print(f"Connecting to {BACKEND_URL}...")

try:
    with requests.post(BACKEND_URL, json=payload, stream=True) as r:
        r.raise_for_status()
        print("Connected! Listening for events...")
        
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    try:
                        data = json.loads(data_str)
                        print(f"EVENT: {data.get('type')}")
                        if data.get('type') == 'text':
                            print(f"  -> Text: {data['content'][:50]}...")
                        elif data.get('type') == 'tool_use':
                            print(f"  -> Tool Use: {data['tool']}")
                        elif data.get('type') == 'error':
                            print(f"  -> ERROR: {data.get('content')}")
                    except json.JSONDecodeError:
                        print(f"RAW: {decoded_line}")
except Exception as e:
    print(f"Error: {e}")
