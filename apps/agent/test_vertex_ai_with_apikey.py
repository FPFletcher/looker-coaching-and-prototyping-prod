from google import genai
from google.genai import types

vertex_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"
project = "antigravity-innovations"
location = "europe-west1"

try:
    print("Testing Vertex AI client with explicit API Key...")
    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
        api_key=vertex_key
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents="Explain how AI works in a few words"
    )
    print("SUCCESS on Vertex:", response.text)
except Exception as e:
    print("FAILED on Vertex:", e)
