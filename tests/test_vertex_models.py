import asyncio
from anthropic import AsyncAnthropicVertex

async def main():
    try:
        client = AsyncAnthropicVertex(region="europe-west1", project_id="looker-core-demo-ffrancois")
        response = await client.messages.create(
            model="claude-3-5-sonnet-v2@20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "hello"}]
        )
        print("Sonnet success!")
    except Exception as e:
        print(f"Sonnet error: {e}")

asyncio.run(main())
