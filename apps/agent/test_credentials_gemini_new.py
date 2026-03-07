from google import genai

gemini_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"

try:
    print("Initializing client with Google GenAI...")
    client = genai.Client(api_key=gemini_key)
    print("Client initialized. Testing model listing...")
    models = list(client.models.list())
    print(f"Success! Found {len(models)} models.")
    for m in models[:5]:
        print(f" - {m.name}")
except Exception as e:
    print(f"Failed with Gemini key: {e}")
