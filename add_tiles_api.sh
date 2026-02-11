#!/bin/bash
set -e

# Looker credentials
LOOKER_URL="https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
CLIENT_ID="vQyY8tbjsT6tcG7ZV85N"
CLIENT_SECRET="hyPbyWkJXDz8h6tGcYk5Y44G"
DASHBOARD_ID="44"

echo "Getting Looker access token..."
TOKEN_RESPONSE=$(curl -s -X POST "${LOOKER_URL}/api/4.0/login" \
  -d "client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo "$TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Got access token"

# Create a simple query and add it to the dashboard
echo ""
echo "Creating query for Total Revenue..."
QUERY_JSON='{
  "model": "advanced_ecomm",
  "view": "order_items",
  "fields": ["order_items.total_sale_price"],
  "limit": "1"
}'

QUERY_RESPONSE=$(curl -s -X POST "${LOOKER_URL}/api/4.0/queries" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON")

QUERY_ID=$(echo "$QUERY_RESPONSE" | jq -r '.id')

if [ "$QUERY_ID" == "null" ] || [ -z "$QUERY_ID" ]; then
    echo "❌ Failed to create query"
    echo "$QUERY_RESPONSE"
    exit 1
fi

echo "✅ Created query ID: $QUERY_ID"

# Add dashboard element
echo ""
echo "Adding dashboard element..."
ELEMENT_JSON="{
  \"dashboard_id\": \"${DASHBOARD_ID}\",
  \"title\": \"Total Revenue\",
  \"query_id\": ${QUERY_ID},
  \"type\": \"vis\"
}"

ELEMENT_RESPONSE=$(curl -s -X POST "${LOOKER_URL}/api/4.0/dashboard_elements" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$ELEMENT_JSON")

ELEMENT_ID=$(echo "$ELEMENT_RESPONSE" | jq -r '.id')

if [ "$ELEMENT_ID" == "null" ] || [ -z "$ELEMENT_ID" ]; then
    echo "❌ Failed to create dashboard element"
    echo "$ELEMENT_RESPONSE"
    exit 1
fi

echo "✅ Successfully added dashboard element ID: $ELEMENT_ID"
echo ""
echo "✅ Dashboard URL: ${LOOKER_URL}/dashboards/${DASHBOARD_ID}"
