import os
import json
from anthropic import Anthropic

anthropic_key = "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"

print("--- Testing Anthropic (with Anthropic Key) ---")
try:
    client = Anthropic(api_key=anthropic_key)
    # The actual valid model name in SDK could be 'claude-3-5-sonnet-20240620'
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=100,
        messages=[{"role": "user", "content": "What is 2+2?"}]
    )
    print("Anthropic SUCCESS:", message.content[0].text)
except Exception as e:
    print("Anthropic FAILED:", str(e))
