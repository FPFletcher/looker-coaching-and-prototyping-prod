from google.genai import types
import json

schema = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"}
    },
    "required": ["query"]
}

try:
    tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_web",
                description="Search the web",
                parameters=schema
            )
        ]
    )
    print("Success natively passing schema")
except Exception as e:
    print(f"Error: {e}")

