# MCP Looker Connection Diagnostic & Testing Tools

This directory contains tools to diagnose and test the MCP server connection to Looker.

## Problem Description

The MCP server appears to not be connecting properly to the Looker instance, with tools like `get_connections`, `get_models`, etc. returning empty results.

## Diagnostic Tools

### 1. Connection Diagnostic (`diagnose_looker_connection.py`)

This script performs two levels of testing:
- **Direct SDK Test**: Tests if the Looker SDK can connect directly
- **MCP Server Test**: Tests if the MCP server can connect through the agent

**Usage:**
```bash
cd /home/admin_ffrancois_altostrat_com/Desktop/Antigravity\ projects

python tests/diagnose_looker_connection.py \
  --looker-url "YOUR_LOOKER_URL" \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET"
```

**What it tests:**
- ✅ Authentication
- ✅ Connections API
- ✅ Projects API
- ✅ Workspace/Dev Mode
- ✅ MCP tool execution

### 2. Comprehensive Tool Test (`test_all_tools.py`)

This script tests ALL MCP tools to ensure they're functional.

**Usage:**
```bash
python tests/test_all_tools.py \
  --looker-url "YOUR_LOOKER_URL" \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --project-id "YOUR_PROJECT_ID"
```

**What it tests:**
- Connection & Authentication (dev_mode, get_connections)
- Project & File Operations (get_project_files, validate_project, etc.)
- LookML Creation (create_project_file)
- Context Tools (register_lookml_manually, get_explore_fields_from_context)
- Database Metadata (get_connection_schemas, get_connection_tables, etc.)
- Visualization Tools (create_dashboard, add_dashboard_element)
- Utility Tools (search_web)
- Health Check Tools (health_pulse)

**Output:**
- Console output with color-coded results
- JSON file: `tool_test_results.json` with detailed results

## Common Issues & Solutions

### Issue 1: Empty Connections/Models

**Symptoms:**
- `get_connections` returns empty array
- `get_models` returns empty array
- Tools appear to execute but return no data

**Possible Causes:**
1. **Development Mode Not Enabled**: Some APIs require dev mode
2. **Wrong Workspace**: User might be in production workspace
3. **Permissions**: API credentials might not have sufficient permissions
4. **Instance Has No Data**: The Looker instance might be empty

**Solutions:**
1. Run diagnostic script to identify the exact issue
2. Ensure dev mode is enabled: `dev_mode(enable=True)`
3. Check user permissions in Looker admin
4. Verify the instance has connections/models configured

### Issue 2: MCP Server Not Finding Toolbox Binary

**Symptoms:**
- Direct SDK works but MCP server fails
- Error about toolbox binary not found

**Solutions:**
1. Check if `mcp-toolbox` binary exists and is executable
2. Verify the path in `MCPAgent.__init__`
3. Install/reinstall the MCP toolbox

### Issue 3: Credentials Not Being Passed

**Symptoms:**
- Authentication errors
- "Invalid credentials" messages

**Solutions:**
1. Verify credentials are correct
2. Check environment variables are being set properly
3. Ensure URL includes protocol (https://)

## Next Steps

1. **Run Diagnostic First:**
   ```bash
   python tests/diagnose_looker_connection.py --looker-url <url> --client-id <id> --client-secret <secret>
   ```

2. **If Diagnostic Passes, Run Full Test:**
   ```bash
   python tests/test_all_tools.py --looker-url <url> --client-id <id> --client-secret <secret> --project-id <project>
   ```

3. **Review Results:**
   - Check console output for failures
   - Review `tool_test_results.json` for details
   - Fix any identified issues

4. **Test in Frontend:**
   - Once backend tests pass, test through the web interface
   - Verify tools work end-to-end

## Files Created

- `tests/diagnose_looker_connection.py` - Connection diagnostic tool
- `tests/test_all_tools.py` - Comprehensive tool test suite
- `tests/TESTING_README.md` - This file
