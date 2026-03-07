import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")

async def test():
    if not api_key:
        print("No ANTHROPIC_API_KEY")
        return
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4-5"
        )
        print("Success:", resp.content)
    except Exception as e:
        print("Error:", e)
        
if __name__ == "__main__":
    asyncio.run(test())
