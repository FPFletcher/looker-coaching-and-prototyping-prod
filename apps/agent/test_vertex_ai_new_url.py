import requests

vertex_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"
model = "claude-sonnet-4-5@20250929"
project = "antigravity-innovations"
location = "europe-west1"
# Specific URL format shown for querying the publisher:
url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/anthropic/models/{model}:rawPredict?key={vertex_key}"

payload = {
  "prompt": "\n\nHuman: Explain how AI works in a few words\n\nAssistant:",
  "max_tokens_to_sample": 100
}

response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
if response.status_code == 200:
    print("SUCCESS on Raw Vertex HTTP.")
    print(response.text)
else:
    print("FAILED on Raw Vertex HTTP:", response.status_code, response.text)
