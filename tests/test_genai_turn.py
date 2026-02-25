import asyncio
from google import genai
from google.genai import types

async def main():
    client = genai.Client(vertexai=True, location="europe-west1", project="looker-core-demo-ffrancois")
    
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
    tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="search_web", description="search", parameters=schema)])
    config = types.GenerateContentConfig(tools=[tool])
    
    # 1. First request
    contents = [types.Content(role="user", parts=[types.Part.from_text(text="Search weather in paris")])]
    first_response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config
    )
    
    # 2. Extract tool call
    fc = first_response.candidates[0].content.parts[0].function_call
    print(f"Tool called: {fc.name}")
    
    # 3. Append to history
    contents.append(first_response.candidates[0].content)
    
    # 4. Add tool response
    tool_resp_part = types.Part.from_function_response(name=fc.name, response={"result": "It is raining and 15C in Paris"})
    contents.append(types.Content(role="user", parts=[tool_resp_part]))
    
    # 5. Second request
    second_response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config
    )
    print(f"Final response: {second_response.text}")

asyncio.run(main())
