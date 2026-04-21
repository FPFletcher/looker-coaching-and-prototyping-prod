import os
import json
from google import genai
from google.genai import types
from google.oauth2 import credentials as google_credentials

token = "ya29.a0Aa7MYirO7qA3AMvQhcxwfAvdFKffu8qdqJDluwRauM5V4iNrfObj1dNQA06BxNfcClrsW-TJlxddVnYRHSuPZzjKdlWVIRxGmHbxtl2JB8Bo-ELGO-Ni3yap95M0mXockjTALCeVcUaRIR_enlNuLAR_wYAoqQGGhVNYd6AsCAqNtIVGYGDdu1fwtwWX1oJJUmFS8iAAaCgYKAZ8SARMSFQHGX2MiBc8wYm_xEmf-NxJ5GnzTjw0207"
project = "antigravity-innovations"
location = "us-central1" # Changed to us-central1
model = "gemini-3.1-pro-preview"

try:
    print(f"Testing Vertex AI with token and model {model} in region {location}...")
    
    creds = google_credentials.Credentials(token)
    
    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
        credentials=creds
    )
    
    response = client.models.generate_content(
        model=model,
        contents="Explain how AI works in a few words"
    )
    print("SUCCESS:", response.text)
except Exception as e:
    print("FAILED:", e)
    import traceback
    traceback.print_exc()
