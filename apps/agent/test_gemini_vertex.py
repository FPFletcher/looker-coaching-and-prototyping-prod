from google import genai
from google.genai import types

gemini_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"

try:
    print("Initializing GENERATIVEAI with API key...")
    client = genai.Client(api_key=gemini_key)
    print("Client initialized. Testing model listing...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="What is 2+2?"
    )
    print("SUCCESS on Generative AI SDK:", response.text)
except Exception as e:
    print("FAILED on Generative AI SDK:", str(e))
