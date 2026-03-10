from google.oauth2 import service_account
from anthropic import AnthropicVertex
import json

with open("sa-key.json", "r") as f:
    sa_info = json.load(f)

creds = service_account.Credentials.from_service_account_info(
    sa_info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

try:
    client = AnthropicVertex(project_id="antigravity-innovations", region="europe-west1", credentials=creds)
    print("AnthropicVertex accepts credentials.")
except Exception as e:
    print("AnthropicVertex error:", str(e))
