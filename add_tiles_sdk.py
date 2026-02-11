#!/usr/bin/env python3
"""
Add dashboard tiles using Looker SDK directly.
"""
import looker_sdk
from looker_sdk import models40 as models

# Initialize SDK
sdk = looker_sdk.init40()

dashboard_id = "44"

print(f"Adding tiles to dashboard {dashboard_id}...")

# Get the dashboard first to verify it exists
try:
    dashboard = sdk.dashboard(dashboard_id)
    print(f"✅ Found dashboard: {dashboard.title}")
except Exception as e:
    print(f"❌ Error finding dashboard: {e}")
    exit(1)

# Define tiles to add
tiles_config = [
    {
        "title": "Total Revenue",
        "model": "advanced_ecomm",
        "explore": "order_items",
        "fields": ["order_items.total_sale_price"],
        "vis_config": {
            "type": "single_value"
        }
    },
    {
        "title": "Total Orders",
        "model": "advanced_ecomm",
        "explore": "orders",
        "fields": ["orders.count"],
        "vis_config": {
            "type": "single_value"
        }
    },
    {
        "title": "Revenue by Month",
        "model": "advanced_ecomm",
        "explore": "order_items",
        "fields": ["orders.created_month", "order_items.total_sale_price"],
        "vis_config": {
            "type": "looker_line"
        }
    }
]

# Add each tile
for i, tile_config in enumerate(tiles_config, 1):
    print(f"\n[{i}/{len(tiles_config)}] Adding: {tile_config['title']}")
    
    try:
        # Create query
        query = models.WriteQuery(
            model=tile_config["model"],
            view=tile_config["explore"],
            fields=tile_config["fields"],
            limit="500"
        )
        
        created_query = sdk.create_query(query)
        print(f"  Created query ID: {created_query.id}")
        
        # Create dashboard element
        element = models.WriteDashboardElement(
            dashboard_id=dashboard_id,
            title=tile_config["title"],
            query_id=created_query.id,
            type="vis"
        )
        
        created_element = sdk.create_dashboard_element(element)
        print(f"✅ Successfully added tile ID: {created_element.id}")
        
    except Exception as e:
        print(f"❌ Failed to add tile: {e}")

print(f"\n✅ Dashboard URL: https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app/dashboards/{dashboard_id}")
