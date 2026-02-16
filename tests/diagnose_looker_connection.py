"""
Looker Connection Diagnostic Script

This script performs basic diagnostics to identify why the MCP server
might not be connecting properly to Looker.

Usage:
    python diagnose_looker_connection.py --looker-url <url> --client-id <id> --client-secret <secret>
"""

import asyncio
import sys
import os
import argparse
import looker_sdk
from looker_sdk import models40

def test_direct_sdk_connection(url: str, client_id: str, client_secret: str):
    """Test direct connection using Looker SDK"""
    print("\n" + "="*80)
    print("TEST 1: Direct Looker SDK Connection")
    print("="*80 + "\n")
    
    try:
        # Set environment variables
        os.environ["LOOKERSDK_BASE_URL"] = url
        os.environ["LOOKERSDK_CLIENT_ID"] = client_id
        os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
        os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
        
        print(f"Connecting to: {url}")
        print(f"Client ID: {client_id[:10]}...")
        
        # Initialize SDK
        sdk = looker_sdk.init40()
        
        # Test 1: Get current user
        print("\n✓ SDK initialized successfully")
        print("\nTesting authentication...")
        me = sdk.me()
        print(f"✅ Authenticated as: {me.display_name} ({me.email})")
        print(f"   User ID: {me.id}")
        
        # Test 2: Get connections
        print("\nTesting connections API...")
        connections = sdk.all_connections()
        print(f"✅ Found {len(connections)} connections:")
        for conn in connections[:5]:  # Show first 5
            print(f"   - {conn.name} ({conn.dialect.name if conn.dialect else 'unknown'})")
        
        # Test 3: Get projects
        print("\nTesting projects API...")
        projects = sdk.all_projects()
        print(f"✅ Found {len(projects)} projects:")
        for proj in projects[:5]:  # Show first 5
            print(f"   - {proj.id} ({proj.name})")
        
        # Test 4: Get workspace
        print("\nTesting workspace...")
        session = sdk.session()
        print(f"✅ Current workspace: {session.workspace_id}")
        
        # Test 5: Enable dev mode
        print("\nTesting dev mode...")
        dev_session = sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
        print(f"✅ Dev mode enabled: {dev_session.workspace_id}")
        
        print("\n" + "="*80)
        print("✅ ALL DIRECT SDK TESTS PASSED")
        print("="*80 + "\n")
        
        return True, connections, projects
        
    except Exception as e:
        print(f"\n❌ DIRECT SDK CONNECTION FAILED")
        print(f"Error: {str(e)}")
        print("\nPossible issues:")
        print("  1. Invalid credentials")
        print("  2. Incorrect Looker URL")
        print("  3. Network/firewall issues")
        print("  4. SSL certificate issues")
        return False, [], []

async def test_mcp_server_connection(url: str, client_id: str, client_secret: str):
    """Test connection through MCP server"""
    print("\n" + "="*80)
    print("TEST 2: MCP Server Connection")
    print("="*80 + "\n")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from apps.agent.mcp_agent import MCPAgent
        
        agent = MCPAgent()
        
        # Test listing tools
        print("Testing tool listing...")
        tools = await agent.list_available_tools(url, client_id, client_secret)
        print(f"✅ Found {len(tools)} tools available")
        
        # Test executing a simple tool
        print("\nTesting tool execution (dev_mode)...")
        result = await agent.execute_tool(
            "dev_mode",
            {"enable": True},
            url,
            client_id,
            client_secret
        )
        
        if result.get("success"):
            print(f"✅ dev_mode executed: {result.get('result')}")
        else:
            print(f"❌ dev_mode failed: {result.get('error')}")
            return False
        
        # Test get_connections
        print("\nTesting tool execution (get_connections)...")
        result = await agent.execute_tool(
            "get_connections",
            {},
            url,
            client_id,
            client_secret
        )
        
        if result.get("success"):
            connections = result.get("result", [])
            print(f"✅ get_connections executed: Found {len(connections)} connections")
            if connections:
                print(f"   First connection: {connections[0]}")
        else:
            print(f"❌ get_connections failed: {result.get('error')}")
            return False
        
        print("\n" + "="*80)
        print("✅ ALL MCP SERVER TESTS PASSED")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ MCP SERVER CONNECTION FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    parser = argparse.ArgumentParser(description="Diagnose Looker connection issues")
    parser.add_argument("--looker-url", required=True, help="Looker instance URL")
    parser.add_argument("--client-id", required=True, help="Looker API client ID")
    parser.add_argument("--client-secret", required=True, help="Looker API client secret")
    
    args = parser.parse_args()
    
    # Ensure URL has protocol
    url = args.looker_url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    print("\n" + "="*80)
    print("LOOKER CONNECTION DIAGNOSTIC TOOL")
    print("="*80)
    print(f"\nLooker URL: {url}")
    print(f"Client ID: {args.client_id[:10]}...")
    
    # Test 1: Direct SDK connection
    sdk_success, connections, projects = test_direct_sdk_connection(
        url,
        args.client_id,
        args.client_secret
    )
    
    if not sdk_success:
        print("\n⚠️  Direct SDK connection failed. Fix this before testing MCP server.")
        sys.exit(1)
    
    # Test 2: MCP server connection
    mcp_success = await test_mcp_server_connection(
        url,
        args.client_id,
        args.client_secret
    )
    
    # Summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80 + "\n")
    
    if sdk_success and mcp_success:
        print("✅ All tests passed! Looker connection is working correctly.")
        print("\nNext steps:")
        print("  1. Run the comprehensive tool test: python tests/test_all_tools.py")
        print("  2. Test the frontend application")
    elif sdk_success and not mcp_success:
        print("⚠️  Direct SDK works but MCP server has issues.")
        print("\nPossible causes:")
        print("  1. MCP toolbox binary not found or not executable")
        print("  2. Environment variables not being passed correctly to MCP server")
        print("  3. MCP server configuration issues")
    else:
        print("❌ Connection failed. Please check your credentials and network.")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
