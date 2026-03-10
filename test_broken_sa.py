import requests
import json
import uuid

url = "http://localhost:8000/api/chat"
headers = {"Content-Type": "application/json"}

broken_sa = json.dumps({
  "type": "service_account",
  "project_id": "test",
  "private_key_id": "123",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDE\n-----END PRIVATE KEY-----\n",
  "client_email": "test@test.iam.gserviceaccount.com",
  "client_id": "123",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test.iam.gserviceaccount.com"
})

data = {
    "message": "Hi",
    "credentials": {
        "url": "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
        "client_id": "Zv36QKRBcC5dpWYTG8nY",
        "client_secret": "hwNSHYBRJqbkhdKm6k2WWykH"
    },
    "model": "gemini-2.0-flash",
    "use_vertex": True,
    "session_id": str(uuid.uuid4()),
    "vertex_api_key": broken_sa
}

resp = requests.post(url, headers=headers, json=data, stream=True)
for line in resp.iter_lines():
    if line:
        print(line.decode("utf-8"))
