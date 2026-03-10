import os
from google import genai
try:
    client = genai.Client(vertexai=True, project="antigravity-innovations", location="europe-west1", api_key="AQ.Ab8RN6IApYrJpLv1jipHJww-hpKCffNayNpfpe7tP66DJjT15w")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='say "bound key works"'
    )
    print("Success with genai Client:", response.text)
except Exception as e:
    print("Failed with genai Client:", str(e))

from anthropic import AnthropicVertex
try:
    # Does anthropic pass api_key?
    pass
except Exception as e:
    print("Failed with anthropic:", str(e))
