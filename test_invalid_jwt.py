import requests
import json
import uuid

url = "http://localhost:8000/api/chat"
headers = {"Content-Type": "application/json"}

# A real-looking base64 private key that is correctly formatted so it passes parsing
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDE2Z5z+\nN2yQOXZ7QhO+P+E8M+p4o8H5W9q+\nPqA1+\nyP2P0S+\n2hQ4O+\nZJ8Nq+Q0O9E+\nR9I2L+p0j7Z+\nb/a3K+\nlL4f9C+\nmQ7k1V+\nL/o5d+\noQx1t+\niL5v8W+\nzZ3t4P+X/E8C+QOXZ7QhO+P+E8M+p4o8H5W9q+\nPqA1+\nyP2P0S+\n2hQ4O+\nZJ8Nq+Q0O9E+\nR9I2L+p0j7Z+\nb/a3K+\nlL4f9C+\nmQ7k1V+\nL/o5d+\noQx1t+\niL5v8W+\nzZ3t4P+X/E8C+QOXZ7QhO+P+E8M+p4o8H5W9q+\nPqA1+\nyP2P0S+\n2hQ4O+\nZJ8Nq+Q0O9E+\nR9I2L+p1A==\n-----END PRIVATE KEY-----\n"

# Actually let's just generate a structurally valid dummy key using cryptography
import subprocess
try:
    subprocess.run(["openssl", "genrsa", "-out", "dummy.pem", "2048"])
    key_pem = open("dummy.pem").read()
except:
    key_pem = private_key

broken_sa = json.dumps({
  "type": "service_account",
  "project_id": "test",
  "private_key_id": "6d9ed9995542a27845ba0bb6ea848bfbb9ebb304",
  "private_key": key_pem,
  "client_email": "fake-service-account@antigravity-innovations.iam.gserviceaccount.com",
  "client_id": "11181827464",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/fake-service-account%40antigravity-innovations.iam.gserviceaccount.com"
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
