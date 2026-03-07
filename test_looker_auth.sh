#!/bin/bash
# Read variables from .env
source apps/agent/.env

echo "Testing Looker Auth for Client ID: $LOOKERSDK_CLIENT_ID"

# Looker Login URL
LOGIN_URL="${LOOKERSDK_BASE_URL}/api/4.0/login"

echo "Requesting Token from $LOGIN_URL..."

# Curl request
response=$(curl -s -X POST "$LOGIN_URL" \
  -d "client_id=$LOOKERSDK_CLIENT_ID" \
  -d "client_secret=$LOOKERSDK_CLIENT_SECRET")

# Check for access_token in response
if echo "$response" | grep -q "access_token"; then
  echo "✅ SUCCESS: Authentication working! Access Token received."
  # echo $response # Don't print full token for security
else
  echo "❌ FAILURE: Authentication failed."
  echo "Response: $response"
fi
