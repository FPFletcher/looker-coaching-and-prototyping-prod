#!/usr/bin/env python3
"""
Test script to directly create dashboard with tiles using the fixed multi-turn approach.
"""
import asyncio
import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'apps/agent/.env'))

# Add apps directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from anthropic import Anthropic

async def main():
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Looker credentials
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    # Import MCP agent to get tools
    from agent.mcp_agent import MCPAgent
    agent = MCPAgent(model_name="claude-sonnet-4-20250514")
    
    # Get available tools
    tools_list = await agent.list_tools(looker_url, client_id, client_secret)
    claude_tools = agent._format_tools_for_claude(tools_list)
    
    print(f"Available tools: {[t['name'] for t in claude_tools]}")
    
    # Create conversation
    messages = [{
        "role": "user",
        "content": "Create a dashboard titled 'Antigravity Retail Dashboard Final' using the advanced_ecomm model. After creating it, add 3 tiles: 1) Total Revenue (single value from order_items.total_sale_price), 2) Total Orders (single value from orders.count), 3) Revenue by Month (line chart with orders.created_month and order_items.total_sale_price). Return the dashboard URL."
    }]
    
    system_prompt = """You are a Looker assistant. When asked to create dashboards and add tiles:
1. First call make_dashboard with the title
2. Then call add_dashboard_element multiple times for each tile
3. Provide the dashboard URL

CRITICAL: You MUST actually call the tools. Do not just describe what you will do."""
    
    # Multi-turn loop
    max_turns = 15
    all_tools_called = []
    
    for turn in range(max_turns):
        print(f"\n=== TURN {turn + 1} ===")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            system=system_prompt,
            messages=messages,
            tools=claude_tools
        )
        
        print(f"Stop reason: {response.stop_reason}")
        
        # Extract text and tool uses
        text_parts = []
        tool_uses = []
        
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                print(f"Text: {block.text[:100]}...")
            elif block.type == "tool_use":
                tool_uses.append(block)
                print(f"Tool call: {block.name}({json.dumps(block.input, indent=2)})")
        
        # If no tools, we're done
        if not tool_uses:
            print(f"\nFinal response: {' '.join(text_parts)}")
            break
        
        # Execute tools
        tool_results = []
        for tool_use in tool_uses:
            print(f"\nExecuting: {tool_use.name}")
            all_tools_called.append(tool_use.name)
            
            result = await agent.execute_tool(
                tool_use.name,
                tool_use.input,
                looker_url,
                client_id,
                client_secret
            )
            
            if result.get("success"):
                result_data = result.get("result", [])
                if isinstance(result_data, list):
                    result_str = ""
                    for item in result_data:
                        if hasattr(item, 'text'):
                            result_str += item.text
                        else:
                            result_str += str(item)
                else:
                    result_str = json.dumps(result_data) if result_data else "Success"
                print(f"  ✅ Success: {result_str[:200]}")
            else:
                result_str = f"Error: {result.get('error', 'Unknown')}"
                print(f"  ❌ {result_str}")
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_str
            })
        
        # Add to conversation
        messages.append({
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": tu.id,
                "name": tu.name,
                "input": tu.input
            } for tu in tool_uses]
        })
        messages.append({
            "role": "user",
            "content": tool_results
        })
    
    print(f"\n\n=== SUMMARY ===")
    print(f"Tools called: {all_tools_called}")
    print(f"Total turns: {turn + 1}")

if __name__ == "__main__":
    asyncio.run(main())
