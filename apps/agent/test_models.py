import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")

async def test_model(model_id):
    if not api_key:
        print("No ANTHROPIC_API_KEY")
        return
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}],
            model=model_id
        )
        print(f"Success for {model_id}:", resp.content)
    except Exception as e:
        print(f"Error for {model_id}:", e)

async def run_tests():
    models = ["claude-3-7-sonnet-20250219", "claude-sonnet-4-6", "claude-opus-4-6"]
    for m in models:
        await test_model(m)
        
if __name__ == "__main__":
    asyncio.run(run_tests())
