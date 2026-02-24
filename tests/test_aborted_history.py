import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/agent')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../apps/agent/.env'))

from mcp_agent import MCPAgent

async def test_aborted_history():
    # Simulate the history created by the frontend when a user stops a generation
    # where the agent had started a tool but didn't finish it
    history = [
        {"role": "user", "content": "Create a dashboard for user logins"},
        {
            "role": "assistant",
            "content": "",
            "parts": [
                {
                    "type": "tool",
                    "tool": "create_dashboard",
                    "input": {"title": "User Logins"},
                    "status": "running" # The user hit stop before the tool finished!
                },
                {
                    "type": "text",
                    "content": "Response stopped by user."
                }
            ]
        }
    ]
    
    agent = MCPAgent(session_id="test_abort_session")
    
    events = []
    # Send a follow-up message
    async for event in agent.process_message(
        "Actually, just tell me what tools you just used.",
        history=history,
        looker_url=os.getenv("LOOKER_BASE_URL", "https://example.com"),
        client_id=os.getenv("LOOKER_CLIENT_ID", "test"),
        client_secret=os.getenv("LOOKER_CLIENT_SECRET", "test")
    ):
        print(f"Event: type={event.get('type')} tool={event.get('tool')}")
        if event.get("type") == "text":
            events.append(event)
            print(f"Text: {event.get('content')}")
        elif event.get("type") == "error":
            print(f"Error: {event.get('content')}")
            
    print("\n--- Final Output ---")
    for e in events:
        print(e.get("content", ""), end="")
        
if __name__ == "__main__":
    asyncio.run(test_aborted_history())
