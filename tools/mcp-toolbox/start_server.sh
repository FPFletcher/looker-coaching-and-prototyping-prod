#!/bin/bash
# Start MCP Toolbox in server mode (persistent)
# This avoids the stdio log interference issue

cd "$(dirname "$0")"

export LOOKER_BASE_URL="${LOOKER_BASE_URL:-https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app}"
export LOOKER_CLIENT_ID="${LOOKER_CLIENT_ID:-vQyY8tbjsT6tcG7ZV85N}"
export LOOKER_CLIENT_SECRET="${LOOKER_CLIENT_SECRET:-hyPbyWkJXDz8h6tGcYk5Y44G}"
export LOOKER_VERIFY_SSL="true"

# Kill any existing toolbox processes
pkill -f "toolbox.*looker" 2>/dev/null || true
sleep 1

# Start toolbox in background, redirecting logs
./toolbox start --prebuilt looker > /dev/null 2>&1 &

echo "MCP Toolbox started on stdio mode"
