import os
from anthropic import Anthropic

anthropic_key = "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"

print("--- Testing Anthropic (Haiku) ---")
try:
    client = Anthropic(api_key=anthropic_key)
    # Testing Claude 3 Haiku
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=100,
        messages=[{"role": "user", "content": "What is 2+2?"}]
    )
    print("Anthropic Haiku SUCCESS:", message.content[0].text)
except Exception as e:
    print("Anthropic Haiku FAILED:", str(e))

