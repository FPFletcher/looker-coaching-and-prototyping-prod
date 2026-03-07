from google import genai

gemini_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"

try:
    print("Testing gemini-2.5-pro...")
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="What is 2+2?"
    )
    print(f"Gemini Pro SUCCESS: {response.text}")
except Exception as e:
    print(f"Failed with gemini-2.5-pro key: {e}")
    
try:
    print("Testing gemini-2.0-flash...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="What is 2+2?"
    )
    print(f"Gemini Flash SUCCESS: {response.text}")
except Exception as e:
    print(f"Failed with gemini-2.0-flash key: {e}")
