#!/usr/bin/env python3
"""
Direct script to add dashboard tiles using Looker MCP tools.
This bypasses the chat interface and calls the tools directly.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'apps/agent/.env'))

# Add apps directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from agent.mcp_agent import MCPAgent

async def main():
    # Initialize agent with Claude
    agent = MCPAgent(model_name="claude-sonnet-4-20250514")
    
    # Looker credentials
    looker_url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    dashboard_id = "44"
    
    print(f"Adding tiles to dashboard {dashboard_id}...")
    
    # Define the tiles to add
    tiles = [
        {
            "title": "Total Revenue",
            "model": "advanced_ecomm",
            "explore": "order_items",
            "fields": ["order_items.total_sale_price"],
            "vis_type": "single_value"
        },
        {
            "title": "Total Orders",
            "model": "advanced_ecomm",
            "explore": "orders",
            "fields": ["orders.count"],
            "vis_type": "single_value"
        },
        {
            "title": "Revenue by Month",
            "model": "advanced_ecomm",
            "explore": "order_items",
            "fields": ["orders.created_month", "order_items.total_sale_price"],
            "vis_type": "looker_line"
        }
    ]
    
    for i, tile in enumerate(tiles, 1):
        print(f"\n[{i}/{len(tiles)}] Adding: {tile['title']}")
        
        # Build query fields
        fields_str = ",".join(tile["fields"])
        
        # Call add_dashboard_element tool
        result = await agent.execute_tool(
            tool_name="add_dashboard_element",
            arguments={
                "dashboard_id": dashboard_id,
                "title": tile["title"],
                "model": tile["model"],
                "explore": tile["explore"],
                "fields": fields_str,
                "vis_type": tile.get("vis_type", "looker_column")
            },
            looker_url=looker_url,
            client_id=client_id,
            client_secret=client_secret
        )
        
        if result.get("success"):
            print(f"✅ Successfully added: {tile['title']}")
        else:
            print(f"❌ Failed to add: {tile['title']}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n✅ Dashboard URL: {looker_url}/dashboards/{dashboard_id}")

if __name__ == "__main__":
    asyncio.run(main())
