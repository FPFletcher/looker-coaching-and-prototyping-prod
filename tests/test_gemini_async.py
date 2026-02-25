from google import genai
from google.genai import types
import asyncio

async def test():
    client = genai.Client(vertexai=True, location="europe-west1", project="looker-core-demo-ffrancois")
    config = types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE")
        ]
    )
    result = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say hi",
        config=config
    )
    print(result.text)

asyncio.run(test())
