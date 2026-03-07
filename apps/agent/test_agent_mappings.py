import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Add agent path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_agent import MCPAgent

def test_mappings():
    models_to_test = [
        "claude-sonnet-4-6@defaultclaude",
        "claude-opus-4-6@defaultclaude",
        "claude-sonnet-4-5",
    ]
    
    print("--- DIRECT API MODE (No Vertex/GCP creds) ---")
    
    # Force direct API mode by removing vertex creds
    old_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    old_vertex = os.environ.get("VERTEX_API_KEY")
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    if "VERTEX_API_KEY" in os.environ:
        del os.environ["VERTEX_API_KEY"]
    
    # Must have Anthropic key to trigger Claude Direct API
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = "dummy_key"

    for model in models_to_test:
        try:
            agent = MCPAgent(model_name=model)
            print(f"Input: {model} | Output self.model_name: {agent.model_name} | is_vertex: {agent.is_vertex}")
        except Exception as e:
            print(f"Input: {model} | Error: {e}")

    # Restore 
    if old_creds:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = old_creds
    if old_vertex:
        os.environ["VERTEX_API_KEY"] = old_vertex

    print("\n--- VERTEX API MODE ---")
    
    for model in models_to_test:
        try:
            agent = MCPAgent(model_name=model)
            print(f"Input: {model} | Output self.model_name: {agent.model_name} | is_vertex: {agent.is_vertex}")
        except Exception as e:
            print(f"Input: {model} | Error: {e}")

if __name__ == "__main__":
    test_mappings()
