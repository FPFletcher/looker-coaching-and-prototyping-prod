import requests

vertex_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"
model = "gemini-2.5-flash-lite"
url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:streamGenerateContent?key={vertex_key}"

payload = {
  "contents": [
    {
      "role": "user",
      "parts": [
        {
          "text": "Explain how AI works in a few words"
        }
      ]
    }
  ]
}

response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
if response.status_code == 200:
    print("SUCCESS on Raw Vertex HTTP.")
    print(response.text)
else:
    print("FAILED on Raw Vertex HTTP:", response.status_code, response.text)
