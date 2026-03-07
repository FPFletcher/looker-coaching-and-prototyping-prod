from google import genai
import inspect

# Initialize proper setup
api_key = "AIzaSyAoluI2x4o3K3W0lZXIi_cxgwyRuMjmEHc"

try:
    print("Initializing client with Google GenAI...")
    client = genai.Client(api_key=api_key)
    print("Client initialized. Testing model listing...")
    models = list(client.models.list())
    print(f"Success! Found {len(models)} models.")
    for m in models[:5]:
        print(f" - {m.name}")
except Exception as e:
    print(f"Failed with AIza key directly: {e}")
