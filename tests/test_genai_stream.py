import asyncio
from google import genai
from google.genai import types

async def main():
    try:
        print("Initializing client...")
        client = genai.Client(vertexai=True, location="europe-west1", project="looker-core-demo-ffrancois")
        
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }

        tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_web",
                    description="Search the web",
                    parameters=schema
                )
            ]
        )
        
        config = types.GenerateContentConfig(tools=[tool])
        
        print("Calling API...")
        response = await client.aio.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents="Please search the web for the weather in Paris",
            config=config
        )
        
        print("Iterating response...")
        async for chunk in response:
            print(f"Got chunk: {type(chunk)}")
            if hasattr(chunk, 'function_calls') and chunk.function_calls:
                for fc in chunk.function_calls:
                    print(f"Tool format: name={fc.name} args={fc.args}")
                    
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
