import subprocess
import os

vertex_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"
project = "antigravity-innovations"
location = "europe-west1"
model = "claude-sonnet-4-5@20250929"

# We use the correct endpoint for Anthropic Vertex API calls via raw curl using the key query parameter!
curl_cmd = f"""curl -s -X POST "https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/anthropic/models/{model}:streamGenerateContent?key={vertex_key}" -H "Content-Type: application/json" -d '{{"contents":[{{"role":"user","parts":[{{"text":"Explain how AI works in a few words"}}]}}]}}'"""

print(curl_cmd)
result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
print("Return:", result.returncode)
print("Output:", result.stdout)
print("Error:", result.stderr)

