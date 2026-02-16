"""
Comprehensive MCP Tool Test Suite

This script tests ALL tools available in the MCP agent to ensure they're properly
connected to the Looker instance and functioning correctly.

Usage:
    python test_all_tools.py --looker-url <url> --client-id <id> --client-secret <secret> --project-id <project>
"""

import asyncio
import sys
import os
import argparse
import json
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from apps.agent.mcp_agent import MCPAgent

class ToolTester:
    def __init__(self, looker_url: str, client_id: str, client_secret: str, project_id: str):
        self.looker_url = looker_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.agent = MCPAgent()
        self.results = []
        
    def log_result(self, tool_name: str, status: str, message: str, details: Any = None):
        """Log test result"""
        result = {
            "tool": tool_name,
            "status": status,  # "PASS", "FAIL", "SKIP"
            "message": message,
            "details": details
        }
        self.results.append(result)
        
        # Print colored output
        color = "\033[92m" if status == "PASS" else "\033[91m" if status == "FAIL" else "\033[93m"
        reset = "\033[0m"
        print(f"{color}[{status}]{reset} {tool_name}: {message}")
        if details and status == "FAIL":
            print(f"  Details: {details}")
    
    async def test_tool(self, tool_name: str, args: Dict[str, Any], expected_keys: List[str] = None):
        """Test a single tool"""
        try:
            result = await self.agent.execute_tool(
                tool_name,
                args,
                self.looker_url,
                self.client_id,
                self.client_secret
            )
            
            if result.get("success"):
                # Check for expected keys in result
                if expected_keys:
                    result_data = result.get("result", {})
                    missing_keys = [k for k in expected_keys if k not in str(result_data)]
                    if missing_keys:
                        self.log_result(tool_name, "FAIL", f"Missing expected keys: {missing_keys}", result)
                    else:
                        self.log_result(tool_name, "PASS", "Tool executed successfully", result.get("result"))
                else:
                    self.log_result(tool_name, "PASS", "Tool executed successfully", result.get("result"))
            else:
                self.log_result(tool_name, "FAIL", result.get("error", "Unknown error"), result)
                
        except Exception as e:
            self.log_result(tool_name, "FAIL", f"Exception: {str(e)}", str(e))
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*80)
        print("MCP TOOL COMPREHENSIVE TEST SUITE")
        print("="*80 + "\n")
        
        print(f"Looker URL: {self.looker_url}")
        print(f"Project ID: {self.project_id}\n")
        
        # ==========================================
        # SECTION 1: CONNECTION & AUTHENTICATION
        # ==========================================
        print("\n--- SECTION 1: Connection & Authentication ---\n")
        
        # Test 1: Enable dev mode
        await self.test_tool("dev_mode", {"enable": True})
        
        # Test 2: Get connections
        await self.test_tool("get_connections", {})
        
        # ==========================================
        # SECTION 2: PROJECT & FILE OPERATIONS
        # ==========================================
        print("\n--- SECTION 2: Project & File Operations ---\n")
        
        # Test 3: Get project files
        await self.test_tool("get_project_files", {"project_id": self.project_id})
        
        # Test 4: Get git branch state
        await self.test_tool("get_git_branch_state", {"project_id": self.project_id})
        
        # Test 5: Validate project
        await self.test_tool("validate_project", {"project_id": self.project_id})
        
        # ==========================================
        # SECTION 3: LOOKML CREATION
        # ==========================================
        print("\n--- SECTION 3: LookML Creation ---\n")
        
        # Test 6: Create a test view file
        test_view_content = """
view: test_view_mcp {
  sql_table_name: public.test_table ;;
  
  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
  }
  
  dimension: name {
    type: string
    sql: ${TABLE}.name ;;
  }
  
  measure: count {
    type: count
  }
}
"""
        await self.test_tool(
            "create_project_file",
            {
                "project_id": self.project_id,
                "path": "test_view_mcp.view.lkml",
                "source": test_view_content
            }
        )
        
        # ==========================================
        # SECTION 4: CONTEXT TOOLS
        # ==========================================
        print("\n--- SECTION 4: Context Tools ---\n")
        
        # Test 7: Register LookML manually (if auto-registration failed)
        await self.test_tool(
            "register_lookml_manually",
            {
                "type": "view",
                "view_name": "test_view_mcp",
                "sql_table_name": "public.test_table",
                "fields": [
                    {"name": "id", "type": "dimension", "field_type": "number"},
                    {"name": "name", "type": "dimension", "field_type": "string"},
                    {"name": "count", "type": "measure", "field_type": "number"}
                ]
            }
        )
        
        # ==========================================
        # SECTION 5: DATABASE METADATA
        # ==========================================
        print("\n--- SECTION 5: Database Metadata ---\n")
        
        # First get connections to find a connection name
        conn_result = await self.agent.execute_tool(
            "get_connections",
            {},
            self.looker_url,
            self.client_id,
            self.client_secret
        )
        
        if conn_result.get("success") and conn_result.get("result"):
            connections = conn_result.get("result", [])
            if connections:
                # Use first connection for testing
                test_conn = connections[0].get("name") if isinstance(connections[0], dict) else str(connections[0])
                
                # Test 8: Get connection schemas
                await self.test_tool("get_connection_schemas", {"connection_name": test_conn})
                
                # Test 9: Get connection tables (requires schema)
                # We'll skip this for now as it requires a valid schema name
                self.log_result("get_connection_tables", "SKIP", "Requires valid schema name")
                
                # Test 10: Get connection columns (requires schema and table)
                self.log_result("get_connection_columns", "SKIP", "Requires valid schema and table name")
            else:
                self.log_result("get_connection_schemas", "SKIP", "No connections available")
                self.log_result("get_connection_tables", "SKIP", "No connections available")
                self.log_result("get_connection_columns", "SKIP", "No connections available")
        else:
            self.log_result("get_connection_schemas", "SKIP", "Could not retrieve connections")
            self.log_result("get_connection_tables", "SKIP", "Could not retrieve connections")
            self.log_result("get_connection_columns", "SKIP", "Could not retrieve connections")
        
        # ==========================================
        # SECTION 6: VISUALIZATION TOOLS
        # ==========================================
        print("\n--- SECTION 6: Visualization Tools ---\n")
        
        # Test 11: Create dashboard
        await self.test_tool(
            "create_dashboard",
            {"title": "MCP Test Dashboard"}
        )
        
        # ==========================================
        # SECTION 7: UTILITY TOOLS
        # ==========================================
        print("\n--- SECTION 7: Utility Tools ---\n")
        
        # Test 12: Search web
        await self.test_tool(
            "search_web",
            {"query": "Looker LookML best practices"}
        )
        
        # ==========================================
        # SECTION 8: HEALTH CHECK TOOLS
        # ==========================================
        print("\n--- SECTION 8: Health Check Tools ---\n")
        
        # Test 13: Health pulse
        await self.test_tool("health_pulse", {})
        
        # ==========================================
        # SUMMARY
        # ==========================================
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"\nSuccess Rate: {(passed/total*100):.1f}%\n")
        
        # Print failed tests
        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  - {r['tool']}: {r['message']}")
        
        # Save results to JSON
        with open("tool_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("\nDetailed results saved to: tool_test_results.json\n")
        
        return passed, failed, skipped

async def main():
    parser = argparse.ArgumentParser(description="Test all MCP tools")
    parser.add_argument("--looker-url", required=True, help="Looker instance URL")
    parser.add_argument("--client-id", required=True, help="Looker API client ID")
    parser.add_argument("--client-secret", required=True, help="Looker API client secret")
    parser.add_argument("--project-id", required=True, help="LookML project ID to test with")
    
    args = parser.parse_args()
    
    tester = ToolTester(
        args.looker_url,
        args.client_id,
        args.client_secret,
        args.project_id
    )
    
    passed, failed, skipped = await tester.run_all_tests()
    
    # Exit with error code if any tests failed
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    asyncio.run(main())
