import os
import json
from google import genai
from anthropic import Anthropic

gemini_key = "AIzaSyD0dlDQIv6mOIQxLm_EH63QPcFXFuiZ8PM"
anthropic_key = "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"

print("--- Testing Anthropic NEW model version name ---")
try:
    client = Anthropic(api_key=anthropic_key)
    # Testing Claude 3.5 Sonnet (new release)
    model_name = "claude-3-5-sonnet-20241022"
    message = client.messages.create(
        model=model_name,
        max_tokens=100,
        messages=[{"role": "user", "content": "What is 2+2?"}]
    )
    print("Anthropic SUCCESS with model", model_name, ":", message.content[0].text)
except Exception as e:
    print("Anthropic FAILED:", str(e))

print("--- Testing Gemini NEW model version name ---")
try:
    client = genai.Client(api_key=gemini_key)
    # Testing Gemini 2.5 Pro
    model_name = "gemini-2.5-pro"
    response = client.models.generate_content(model=model_name, contents="What is 2+2?")
    print("Gemini SUCCESS with model", model_name, ":", response.text)
except Exception as e:
    print("Gemini FAILED:", str(e))

