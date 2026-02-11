# Looker MCP Tools Investigation

## Current Status
- **Tools Available**: 15 tools via `--prebuilt looker`
- **Expected**: 50+ tools based on MCP Looker documentation

## Available Tools (Current)
1. `query_url` - Run a query with a Looker model and return query against that model
2. `make_dashboard` - Create a new Looker dashboard
3. `get_filters` - Get filters for a given Explore
4. `make_look` - Create a saved Look in Looker for a query
5. `add_dashboard_element` - Add a query to an existing Looker dashboard
6. `get_dashboards` - Get all dashboards in a Looker instance
7. `get_explores` - Get all Explores for a given model
8. `get_dimensions` - Get all dimensions for a given Explore
9. `get_looks` - Get all Looks in a Looker instance
10. `query_sql` - Run a SQL query against a Looker model
11. `query` - Run a query against a Looker model
12. `get_models` - Get all models in a Looker instance
13. `get_measures` - Get all measures for a given Explore
14. `run_look` - Run a saved Look by ID
15. `get_parameters` - Get all parameters for a given Explore

## Missing Tools (from documentation)
Based on the uploaded image, the following tool categories are documented but not available:

### Looker Content Tools
- `edit_look` - Create a saved Look in Looker and return the URL
- `get_look_url` - Get the URL for a Look by ID or description
- `edit_dashboard` - Create a saved dashboard in Looker and return the URL
- `get_dashboard_url` - Get the URL for a dashboard by ID or description

### Looker Instance Health Tools
- `health_pulse` - Check the health of a Looker instance
- `health_db_connections` - Check the health of database connections
- `health_viewer` - Print LookML elements that might be unused

### LookML Management Tools
- `dev_mode` - Turn on or off the dev mode for a session
- `git_connection_schema` - Get the list of schemas for a connection
- `git_connection_tables` - Get the list of tables for a connection
- `git_connection_columns` - Get the list of columns for a connection
- `create_project_file` - Create a new LookML file
- `update_project_file` - Update an existing LookML file
- `delete_project_file` - Delete a LookML file
- `git_project_branch` - Get the list of available LookML projects
- `git_project_commit` - Get the list of commits for a LookML project
- `git_project_deploy` - Create a new LookML file

## Hypothesis
The `--prebuilt looker` configuration only includes the most common/essential tools for querying and basic dashboard creation. The full set of tools may require:
1. A custom tools configuration file
2. Different prebuilt configuration
3. Additional environment variables or permissions

## Next Steps
1. ✅ Add clickable tools modal to UI
2. Check if there's a way to enable all tools
3. Consider creating custom tool configuration if needed
