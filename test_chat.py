import requests
import json

url = "http://localhost:8000/api/chat"
headers = {"Content-Type": "application/json"}
data = {
    "message": "Hi",
    "credentials": {
        "url": "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
        "client_id": "Zv36QKRBcC5dpWYTG8nY",
        "client_secret": "hwNSHYBRJqbkhdKm6k2WWykH"
    },
    "model": "claude-sonnet-4-5",
    "use_vertex": True,
    "claude_api_key": "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"
}

resp = requests.post(url, headers=headers, json=data, stream=True)
for line in resp.iter_lines():
    if line:
        print(line.decode('utf-8'))
