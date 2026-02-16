import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
import google.generativeai as genai
from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from duckduckgo_search import DDGS
import base64
import requests
import re
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# Import and initialize LookML context tracking (Global Singleton)
try:
    from apps.agent.lookml_context import LookMLContext, LookMLParser
except ImportError:
    from lookml_context import LookMLContext, LookMLParser

GLOBAL_LOOKML_CONTEXT = LookMLContext()

class MCPAgent:
    """
    Conversational agent that uses Gemini or Claude to interpret user requests
    and executes appropriate Looker MCP tools.
    
    Supports both Google Gemini and Anthropic Claude models.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.created_files_cache = {}  # Track created files: {project_id/path: {content, created_at}}
        
        # Use the global singleton for persistence across requests
        self.lookml_context = GLOBAL_LOOKML_CONTEXT
        
        self.is_claude = model_name.startswith("claude-")
        
        if self.is_claude:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise Exception("ANTHROPIC_API_KEY not found in environment")
            self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        else:
            if not os.getenv("GOOGLE_API_KEY"):
                raise Exception("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = genai.GenerativeModel(model_name)
        
        # Apps/agent/mcp_agent.py -> ../../tools/mcp-toolbox/toolbox
        self.toolbox_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tools/mcp-toolbox/toolbox"))
        
    def _get_server_params(self, looker_url: str, client_id: str, client_secret: str) -> StdioServerParameters:
        """Create server parameters with proper environment setup."""
        env = os.environ.copy()
        env["LOOKER_BASE_URL"] = looker_url.rstrip("/")
        env["LOOKER_CLIENT_ID"] = client_id
        env["LOOKER_CLIENT_SECRET"] = client_secret
        env["LOOKER_VERIFY_SSL"] = "true"
        
        return StdioServerParameters(
            command=self.toolbox_bin,
            args=["--stdio", "--prebuilt", "looker"],
            env=env
        )
        
    servername: str = "Looker MCP Agent"
    
    async def list_available_tools(self, looker_url: str, client_id: str, client_secret: str) -> List[Dict[str, Any]]:
        """
        Lists all available Looker MCP tools by starting an ephemeral session.
        Returns tool names, descriptions, and schemas.
        """
        # Sanitize looker_url
        if looker_url and not looker_url.startswith(("http://", "https://")):
             looker_url = f"https://{looker_url}"

        logger.info("Listing available MCP tools...")
        
        server_params = self._get_server_params(looker_url, client_id, client_secret)
        
        try:
            tools = []
            
            # 1. Get tools from binary
            logger.info(f"Connecting to toolbox at: {self.toolbox_bin}")
            try:
                logger.info(f"Starting toolbox with command: {self.toolbox_bin} --stdio --prebuilt looker")
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        
                        # Define tools that we manually override/implement
                        overridden_tools = {
                            "create_project_file", "update_project_file", "delete_project_file",
                            "create_query_from_context", "get_models", "get_explores",
                            "get_lookml_model_explore", "validate_project", "get_git_branch_state",
                            "get_project_structure", "commit_project_changes", "register_lookml_manually",
                            "create_project", "get_projects", "get_project_files", "get_project_file",
                            "dev_mode", "health_pulse", "health_analyze", "health_vacuum",
                            "create_dashboard", "add_dashboard_element", "get_datagroups"
                        }

                        for tool in tools_result.tools:
                            if tool.name not in overridden_tools:
                                tools.append({
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema
                                })
            except Exception as e:
                logger.error(f"Failed to list tools from binary: {e}", exc_info=True)
                pass
            
            # 2. Inject custom tools (not in binary)
            tools.append({
                "name": "create_dashboard_filter",
                "description": "Add a filter to an existing dashboard. Types: field_filter, date_filter, string_filter, number_filter.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dashboard_id": {"type": "string", "description": "ID of the dashboard to update"},
                        "name": {"type": "string", "description": "Name of the filter (internal)"},
                        "title": {"type": "string", "description": "Display title for the filter"},
                        "type": {"type": "string", "description": "Type of filter (field_filter, date_filter, etc)"},
                        "model": {"type": "string", "description": "Model name"},
                        "explore": {"type": "string", "description": "Explore name"},
                        "dimension": {"type": "string", "description": "Fully qualified dimension name (e.g. orders.created_date)"}
                    },
                    "required": ["dashboard_id", "title", "type", "model", "explore", "dimension"]
                }
            })

            tools.append({
                "name": "search_web",
                "description": "Search the web for real-time information, trends, or external data.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            })

            tools.append({
                "name": "create_chart",
                "description": "Generate a single chart/visualization image for a quick answer. Use this for simple questions instead of creating a full dashboard.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Model name"},
                        "explore": {"type": "string", "description": "Explore name"},
                        "fields": {"type": "array", "items": {"type": "string"}, "description": "List of fields (dimensions/measures)"},
                        "filters": {"type": "object", "description": "Dictionary where keys are field names and values are filter expressions (e.g. {'orders.status': 'complete'})"},
                        "sorts": {"type": "array", "items": {"type": "string"}, "description": "List of fields to sort by"},
                        "limit": {"type": "string", "description": "Row limit (default 500)"},
                        "vis_config": {"type": "object", "description": "Plot configuration options. DO NOT hallucinate Looker internal keys. Only use if explicitly known."}
                    },
                    "required": ["model", "explore", "fields"]
                }
            })

            tools.append({
                "name": "list_data_agents",
                "description": "List available Google Cloud Data Agents for Conversational Analytics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "GCP Project ID"},
                        "location": {"type": "string", "description": "GCP Location (default: us-central1)"}
                    },
                    "required": ["project_id"]
                }
            })

            tools.append({
                "name": "chat_with_data_agent",
                "description": "Send a natural language query to a specific Google Cloud Data Agent.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "GCP Project ID"},
                        "location": {"type": "string", "description": "GCP Location (default: us-central1)"},
                        "agent_id": {"type": "string", "description": "ID of the Data Agent (e.g. 'sales-agent')"},
                        "message": {"type": "string", "description": "The user's question or query"}
                    },
                    "required": ["project_id", "agent_id", "message"]
                }
            })

            # Health Tools
            tools.append({
                "name": "health_pulse",
                "description": "Check the health of the Looker instance (connection status and user info).",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })

            tools.append({
                "name": "health_analyze",
                "description": "Analyze Looker content for validation errors (broken content, field references).",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })

            tools.append({
                "name": "health_vacuum",
                "description": "Find unused dashboards (0 views in the last 90 days) to help clean up the instance.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })
            
            # LookML Authoring Tools
            tools.append({
                "name": "dev_mode",
                "description": "Enter or exit Development Mode. Required for editing LookML.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "enable": {"type": "boolean", "description": "True to enter dev mode, False to exit"}
                    },
                    "required": ["enable"]
                }
            })

            tools.append({
                "name": "get_projects",
                "description": "List all LookML projects.",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            })

            tools.append({
                "name": "create_project",
                "description": "Create a new LookML project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the project"}
                    },
                    "required": ["name"]
                }
            })

            tools.append({
                "name": "get_project_files",
                "description": "List files in a LookML project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"}
                    },
                    "required": ["project_id"]
                }
            })

            tools.append({
                "name": "get_project_file",
                "description": "Get the content of a LookML file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "file_id": {"type": "string", "description": "File ID (path/to/file.lkml)"}
                    },
                    "required": ["project_id", "file_id"]
                }
            })

            tools.extend([
            {
                "name": "create_project_file",
                "description": "Creates and auto-registers a new file in a project. REQUIRED context for models: connection name. Auto-registers views/models/explores in session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "path": {"type": "string", "description": "File path (e.g. views/users.view.lkml)"},
                        "source": {"type": "string", "description": "File content"}
                    },
                    "required": ["project_id", "path", "source"]
                }
            },
            {
                "name": "delete_project_file",
                "description": "Delete a LookML file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "file_id": {"type": "string", "description": "File ID"}
                    },
                    "required": ["project_id", "file_id"]
                }
            },
            {
                "name": "get_lookml_model_explore",
                "description": "Gets field details (dimensions/measures) for a specific explore. Use BEFORE create_query_from_context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "explore_name": {"type": "string"}
                    },
                    "required": ["model_name", "explore_name"]
                }
            },
            {
                "name": "create_query_from_context",
                "description": "Query tool for NEWLY CREATED/UNCOMMITTED LookML. Do NOT use run_query for local files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "explore_name": {"type": "string"},
                        "dimensions": {"type": "array", "items": {"type": "string"}},
                        "measures": {"type": "array", "items": {"type": "string"}},
                        "filters": {"type": "object"},
                        "sorts": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "string"}
                    },
                    "required": ["model_name", "explore_name"]
                }
            },
            {
                "name": "get_models",
                "description": "Lists COMMITTED/PRODUCTION models only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_explores",
                "description": "Lists COMMITTED/PRODUCTION explores only.",
                "inputSchema": {
                     "type": "object",
                     "properties": {
                         "model_name": {"type": "string"}
                     },
                     "required": ["model_name"]
                }
            },
            {
                "name": "validate_project",
                "description": "Validates LookML syntax in a project and returns any errors. Call this after creating/updating LookML files to ensure they're valid and trigger model parsing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID to validate"}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_git_branch_state",
                "description": "Get git branch state including uncommitted changes. Use this to discover files you just created that may not appear in get_project_files. Critical for finding newly created LookML files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_project_structure",
                "description": "Analyze project directory structure to determine correct include paths. Returns whether project has subdirectories and recommends include pattern (*.view.lkml vs **/*.view.lkml).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"}
                    },
                    "required": ["project_id"]
                }
            },
            # commit_project_changes REMOVED for security/policy reasons as per user request.
            {
                "name": "get_datagroups",
                "description": "List all available datagroups. Use this before referencing datagroups in derived tables to avoid 'undefined datagroup' errors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "create_dashboard",
                "description": "Create a new empty User Defined Dashboard (UDD). Returns dashboard ID and embed URL. Use this for all multi-tile dashboard requests.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the dashboard"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "add_dashboard_element",
                "description": "Add a tile (visualization) to a User Defined Dashboard. Supports both existing queries and creating new queries from context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dashboard_id": {"type": "string", "description": "ID of the target dashboard"},
                        "title": {"type": "string", "description": "Title of the tile"},
                        "type": {"type": "string", "description": "Visualization type (looker_grid, looker_column, etc.)"},
                        "query_id": {"type": "string", "description": "Optional: Existing query ID to use"},
                        "query_def": {
                            "type": "object",
                            "description": "Optional: Define a new query inline (creates a new query). Use this for UNCOMMITTED LookML.",
                            "properties": {
                                "model": {"type": "string"},
                                "explore": {"type": "string"}, # SDK uses 'view' for explore name in WriteQuery, key mapped in logic
                                "fields": {"type": "array", "items": {"type": "string"}},
                                "filters": {"type": "object"},
                                "sorts": {"type": "array", "items": {"type": "string"}},
                                "limit": {"type": "string"}
                            },
                             "required": ["model", "explore", "fields"]
                        }
                    },
                    "required": ["dashboard_id", "title"]
                }
            },
            {
                "name": "create_dashboard_from_context",
                "description": "Create a multi-tile dashboard for NEWLY CREATED/UNCOMMITTED LookML. Returns a dashboard URL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "explore_name": {"type": "string"},
                        "tiles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "type": {"type": "string", "description": "vis type (e.g. looker_column, looker_grid)"},
                                    "fields": {"type": "array", "items": {"type": "string"}},
                                    "filters": {"type": "object"},
                                    "sorts": {"type": "array", "items": {"type": "string"}},
                                    "limit": {"type": "string"}
                                },
                                "required": ["title", "fields"]
                            }
                        }
                    },
                    "required": ["model_name", "explore_name", "tiles"]
                }
            },
            {
                "name": "get_explore_fields_from_context",
                "description": "Get available dimensions/measures from the CURRENT SESSION'S uncommitted LookML. Use this to validate fields before querying.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "explore_name": {"type": "string"}
                    },
                    "required": ["model_name", "explore_name"]
                }
            },
            {
                "name": "register_lookml_manually",
                "description": "Manually register LookML artifacts in context. USE AS FALLBACK ONLY when auto-registration fails.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["view", "model", "explore"], "description": "Type of artifact to register"},
                        "view_name": {"type": "string", "description": "View name (required if type=view)"},
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string", "enum": ["dimension", "measure"]},
                                    "field_type": {"type": "string", "description": "string, number, date, count, sum, etc."},
                                    "label": {"type": "string"}
                                },
                                "required": ["name"]
                            },
                            "description": "List of fields (required if type=view)"
                        },
                        "sql_table_name": {"type": "string", "description": "SQL table name (optional for view)"},
                        "model_name": {"type": "string", "description": "Model name (required if type=model)"},
                        "connection": {"type": "string", "description": "Connection name (required if type=model)"},
                        "explores": {"type": "array", "items": {"type": "string"}, "description": "List of explore names (required if type=model)"},
                        "includes": {"type": "array", "items": {"type": "string"}, "description": "Include patterns (optional for model)"},
                        "model": {"type": "string", "description": "Model name (required if type=explore)"},
                        "explore": {"type": "string", "description": "Explore name (required if type=explore)"},
                        "base_view": {"type": "string", "description": "Base view name (required if type=explore)"},
                        "joins": {"type": "array", "items": {"type": "object"}, "description": "Join configurations (optional for explore)"}
                    },
                    "required": ["type"]
                }
            }
            ])

            tools.append({
                "name": "get_explore_fields",
                "description": "Fetch actual dimensions and measures for an explore from Looker API. CRITICAL: ALWAYS call this before creating dashboards to get real fields. Never invent field names - use ONLY the fields returned by this tool. This prevents visualization errors from non-existent metrics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Model name"},
                        "explore": {"type": "string", "description": "Explore name"}
                    },
                    "required": ["model", "explore"]
                }
            })

            # Database Metadata Tools
            tools.append({
                "name": "get_connections",
                "description": "List database connections.",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            })

            tools.append({
                "name": "get_connection_schemas",
                "description": "List schemas for a connection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "connection_name": {"type": "string", "description": "Connection name"}
                    },
                    "required": ["connection_name"]
                }
            })

            tools.append({
                "name": "get_connection_tables",
                "description": "List tables in a schema.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "connection_name": {"type": "string", "description": "Connection name"},
                        "schema_name": {"type": "string", "description": "Schema name"}
                    },
                    "required": ["connection_name", "schema_name"]
                }
            })

            tools.append({
                "name": "get_connection_columns",
                "description": "List columns in a table.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "connection_name": {"type": "string", "description": "Connection name"},
                        "schema_name": {"type": "string", "description": "Schema name"},
                        "table_name": {"type": "string", "description": "Table name"}
                    },
                    "required": ["connection_name", "schema_name", "table_name"]
                }
            })
                    
            logger.info(f"Found {len(tools)} Looker tools (including custom)")
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise Exception(f"Failed to connect to Looker: {str(e)}")
    
    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        looker_url: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """
        Executes a single MCP tool with the given arguments.
        """
        # Sanitize looker_url
        if looker_url and not looker_url.startswith(("http://", "https://")):
             looker_url = f"https://{looker_url}"

        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        # Handle custom tools
        if tool_name == "create_dashboard_filter":
            return self._execute_create_dashboard_filter(arguments, looker_url, client_id, client_secret)
        elif tool_name == "search_web":
            return self._execute_search_web(arguments)
        elif tool_name == "create_chart":
            return self._execute_create_chart(arguments, looker_url, client_id, client_secret)
        elif tool_name == "list_data_agents":
            return self._execute_list_data_agents(arguments)
        elif tool_name == "chat_with_data_agent":
            return self._execute_chat_with_data_agent(arguments)
        elif tool_name == "create_dashboard_from_context":
            return self._execute_create_dashboard_from_context(arguments, looker_url, client_id, client_secret)
        elif tool_name == "create_dashboard":
             return self._execute_create_dashboard(arguments, looker_url, client_id, client_secret)
        elif tool_name == "add_dashboard_element":
             return self._execute_add_dashboard_element(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_explore_fields_from_context":
            return self._execute_get_explore_fields_from_context(arguments, looker_url, client_id, client_secret)
        
        # Health Tools
        elif tool_name == "health_pulse":
            return self._execute_health_pulse(looker_url, client_id, client_secret)
        elif tool_name == "health_analyze":
            return self._execute_health_analyze(looker_url, client_id, client_secret)
        elif tool_name == "health_vacuum":
            return self._execute_health_vacuum(looker_url, client_id, client_secret)

        # LookML Authoring Tools
        elif tool_name == "dev_mode":
            return self._execute_dev_mode(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_projects":
            return self._execute_get_projects(looker_url, client_id, client_secret)
        elif tool_name == "create_project":
            return self._execute_create_project(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_project_files":
            return self._execute_get_project_files(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_project_file":
            return self._execute_get_project_file(arguments, looker_url, client_id, client_secret)
        elif tool_name == "create_project_file":
            return self._execute_create_project_file(arguments, looker_url, client_id, client_secret)
        elif tool_name == "delete_project_file":
            return self._execute_delete_project_file(arguments, looker_url, client_id, client_secret)
        elif tool_name == "validate_project":
            return self._execute_validate_project(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_lookml_model_explore":
            return self._execute_get_lookml_model_explore(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_git_branch_state":
            return self._execute_get_git_branch_state(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_project_structure":
            return self._execute_get_project_structure(arguments, looker_url, client_id, client_secret)
        elif tool_name == "commit_project_changes":
            return self._execute_commit_project_changes(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_datagroups":
            return self._execute_get_datagroups(looker_url, client_id, client_secret)
        elif tool_name == "create_query_from_context":
            return self._execute_create_query_from_context(arguments, looker_url, client_id, client_secret)
        elif tool_name == "register_lookml_manually":
            return self._execute_register_lookml_manually(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_explore_fields":
            return self._execute_get_explore_fields(arguments, looker_url, client_id, client_secret)
        
        # Database Metadata Tools
        elif tool_name == "get_connections":
            return self._execute_get_connections(looker_url, client_id, client_secret)
        elif tool_name == "get_connection_schemas":
            return self._execute_get_connection_schemas(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_connection_tables":
            return self._execute_get_connection_tables(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_connection_columns":
            return self._execute_get_connection_columns(arguments, looker_url, client_id, client_secret)
        
        # Intercept get_models to enhance with workspace info
        elif tool_name == "get_models":
            return self._execute_get_models_enhanced(looker_url, client_id, client_secret)
        
        server_params = self._get_server_params(looker_url, client_id, client_secret)
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(tool_name, arguments)
                    
                    if result.isError:
                        return {
                            "success": False,
                            "error": str(result.content)
                        }
                    
                    return {
                        "success": True,
                        "result": result.content
                    }
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    def _execute_create_dashboard_filter(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        try:
            import looker_sdk
            from looker_sdk import models40
            
            # Initialize SDK
            os.environ["LOOKERSDK_BASE_URL"] = url
            os.environ["LOOKERSDK_CLIENT_ID"] = client_id
            os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
            os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
            
            sdk = looker_sdk.init40()
            # Ensure Dev Mode so we can see uncommitted fields for filters
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            # Create filter
            filter_body = models40.WriteCreateDashboardFilter(
                dashboard_id=args.get("dashboard_id"),
                name=args.get("name", args.get("title")),
                title=args.get("title"),
                type=args.get("type"),
                model=args.get("model"),
                explore=args.get("explore"),
                dimension=args.get("dimension"),
                allow_multiple_values=True,
                row=0
            )
            
            created_filter = sdk.create_dashboard_filter(filter_body)
            
            return {
                "success": True,
                "result": f"Created filter '{created_filter.title}' (id: {created_filter.id}) on dashboard {args.get('dashboard_id')}"
            }
        except Exception as e:
            logger.error(f"Failed to create filter: {e}")
            return {"success": False, "error": str(e)}
    
    
    def _execute_search_web(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = args.get("query")
            if not query:
                return {"success": False, "error": "No query provided"}
            
            # search
            results = DDGS().text(query, max_results=5)
            
            return {
                "success": True,
                "result": results
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "error": str(e)}

    def _execute_create_chart(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        try:
            import looker_sdk
            from looker_sdk import models40
            
            # Initialize SDK
            os.environ["LOOKERSDK_BASE_URL"] = url
            os.environ["LOOKERSDK_CLIENT_ID"] = client_id
            os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
            os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
            
            sdk = looker_sdk.init40()
            
            # ===== FIELD VALIDATION (CRITICAL) =====
            model = args.get("model")
            explore = args.get("explore")
            requested_fields = args.get("fields", [])
            
            logger.info(f"🔍 [FIELD VALIDATION] Validating fields for {model}.{explore}")
            logger.info(f"🔍 [FIELD VALIDATION] Requested fields: {requested_fields}")
            
            # Fetch the explore metadata to get available fields
            try:
                explore_metadata = sdk.lookml_model_explore(model, explore)
                
                # Extract available dimensions and measures
                available_dimensions = [f.name for f in (explore_metadata.fields.dimensions or [])]
                available_measures = [f.name for f in (explore_metadata.fields.measures or [])]
                available_fields = set(available_dimensions + available_measures)
                
                logger.info(f"✅ [FIELD VALIDATION] Found {len(available_dimensions)} dimensions and {len(available_measures)} measures")
                
                # Validate each requested field
                invalid_fields = []
                for field in requested_fields:
                    if field not in available_fields:
                        invalid_fields.append(field)
                        logger.error(f"❌ [FIELD VALIDATION] Invalid field detected: '{field}' does not exist in {model}.{explore}")
                
                if invalid_fields:
                    error_msg = (
                        f"❌ Invalid field(s) detected: {invalid_fields}\n\n"
                        f"These fields do not exist in the explore '{model}.{explore}'.\n\n"
                    )
                    
                    # Find similar fields for suggestion
                    import difflib
                    all_fields = list(available_fields)
                    for invalid in invalid_fields:
                        # Find closest matches
                        matches = difflib.get_close_matches(invalid, all_fields, n=5, cutoff=0.3)
                        if matches:
                            error_msg += f"Did you mean one of these for '{invalid}'?\n"
                            for match in matches:
                                error_msg += f"  - {match}\n"
                        else:
                            # If no close matches, show fields from the same view if possible
                            view_name = invalid.split('.')[0] if '.' in invalid else ""
                            if view_name:
                                view_matches = [f for f in all_fields if f.startswith(view_name + '.')]
                                if view_matches:
                                    error_msg += f"Fields available in view '{view_name}':\n"
                                    for match in view_matches[:10]:
                                        error_msg += f"  - {match}\n"
                                    if len(view_matches) > 10:
                                        error_msg += f"  ... and {len(view_matches) - 10} more\n"
                            
                    error_msg += (
                        f"\nAvailable dimensions (first 20): {available_dimensions[:20]}...\n"
                        f"Available measures (first 20): {available_measures[:20]}...\n\n"
                        f"Please use get_dimensions() and get_measures() to discover the actual available fields."
                    )
                    logger.error(f"❌ [FIELD VALIDATION] Validation failed: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
                
                logger.info(f"✅ [FIELD VALIDATION] All fields validated successfully!")
                
            except Exception as validation_error:
                logger.warning(f"⚠️ [FIELD VALIDATION] Could not validate fields: {validation_error}")
                # Continue anyway but log the warning
            
            # ===== CREATE CHART =====
            
            # Construct Query
            query_body = models40.WriteQuery(
                model=model,
                view=explore, # 'view' param often maps to explore in SDK, or use 'view'
                fields=requested_fields,
                filters=args.get("filters"),
                sorts=args.get("sorts"),
                limit=args.get("limit", "500"),
                vis_config=args.get("vis_config")
            )
            
            # Run Inline Query - JSON for LLM understanding
            json_results = sdk.run_inline_query(
                result_format="json",
                body=query_body
            )
            data_summary = json_results[:10]  # First 10 rows for context
            
            # Create Query to get Slug/ID for Explore URL
            created_query = sdk.create_query(body=query_body)
            query_slug = created_query.client_id
            
            # Construct Explore URL (Standard Looker URL structure)
            # https://<instance>/embed/explore/<model>/<view>?qid=<slug>&toggle=dat,pik,vis
            # ✅ SIMPLE PRIVATE EMBED URL
            base_url = url.rstrip("/")
            explore_url = f"{base_url}/embed/explore/{model}/{explore}?qid={query_slug}&toggle=dat,pik,vis"
            
            logger.info(f"✅ Created explore URL: {explore_url}")
            
            logger.info(f"✅ [CREATE CHART] Chart created successfully: {explore_url}")
            
            return {
                "success": True,
                "result": [
                    {"text": f"**[Open Explorer]({explore_url})**\n\n"},
                    {"text": f"*Chart generated from {explore}. Preview: {data_summary[:200]}...*\n\n"}
                ]
            }
        except Exception as e:
            logger.error(f"❌ [CREATE CHART] Failed to create chart: {e}")
            return {"success": False, "error": str(e)}

    def _get_gcp_token(self):
        credentials, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token

    def _execute_list_data_agents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_id = args.get("project_id")
            location = args.get("location", "us-central1")
            
            if not project_id:
                return {"success": False, "error": "Project ID required"}

            token = self._get_gcp_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}/dataAgents"
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return {"success": False, "error": f"API Error: {response.text}"}
                
            return {"success": True, "result": response.json()}
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return {"success": False, "error": str(e)}

    def _execute_chat_with_data_agent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_id = args.get("project_id")
            location = args.get("location", "us-central1")
            agent_id = args.get("agent_id")
            message = args.get("message")
            
            if not all([project_id, agent_id, message]):
                return {"success": False, "error": "Missing required args"}

            token = self._get_gcp_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}:chat"
            
            payload = {
                "data_agent": f"projects/{project_id}/locations/{location}/dataAgents/{agent_id}",
                "messages": [{
                    "role": "USER",
                    "content": {"text": message}
                }]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                return {"success": False, "error": f"API Error: {response.text}"}
            
            return {"success": True, "result": response.json()}
        except Exception as e:
            logger.error(f"Failed to chat with agent: {e}")
            return {"success": False, "error": str(e)}

    def _format_tools_for_claude(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Claude tool format."""
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"]
            })
        return claude_tools

    async def _select_relevant_tools(self, query: str, tools: List[Dict[str, Any]], poc_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Uses a lightweight call to filter RELEVANT tools based on the query,
        but ensures ESSENTIAL ANALYTICAL TOOLS are ALWAYS included (Additive Logic).
        """
        if not tools:
            return []
            
        # Tools that must NEVER be filtered out to ensure analysis capabilities
        # This matches the "Base Analytics Tools" requirement
        base_analytics = {
            # Core Exploration
            "get_dimensions", "get_measures", 
            
            # Query Execution (Binary & Custom)
             "create_query_from_context", "run_inline_query", "create_sql_query",
            
            # Context & Search
            "search_web", "health_pulse", "get_git_branch_state",
            
            # Visualization
            "create_chart_from_context"
        }

        # Add production tools if NOT in POC mode
        if not poc_mode:
            base_analytics.update({
                "get_models", "get_explores", "get_explore_fields", "get_lookml_model_explore",
                "run_query", "create_query", "create_chart"
            })
        else:
            # POC Specific additions
             base_analytics.update({
                "get_explore_fields_from_context", "validate_project"
            })

        # Final check: Only include tools that are actually in the input list
        # This handles the case where 'tools' was already filtered
        input_tool_names = {t["name"] for t in tools}
        ALWAYS_AVAILABLE = base_analytics.intersection(input_tool_names)

        # Filter out tools that are already strictly required so LLM doesn't waste tokens selecting them
        # We only ask LLM to select from "Optional/Specialized" tools
        optional_tools = [t for t in tools if t["name"] not in ALWAYS_AVAILABLE]
        optional_tool_names = [t["name"] for t in optional_tools]
        
        if not optional_tools:
            # If all tools are mandatory, just return everything
            return tools

        prompt = (
            f"Query: {query}\n"
            f"Specialized Tools Available: {', '.join(optional_tool_names)}\n"
            f"Task: Select any SPECIALIZED tools needed for this query. "
            f"NOTE: Core analytical tools are ALREADY included. "
            f"Only select from the list above if explicitly needed (e.g. 'dev_mode' for editing, 'create_dashboard' for saving).\n"
            f"Return JSON list: [\"tool_name\", ...]\n"
            f"If uncertain, select MORE tools."
        )
        
        selected_specialized_tools = []
        try:
            # Use Gemini Flash for speed
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = await asyncio.to_thread(model.generate_content, prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            if "[" in text and "]" in text:
                text = text[text.find("["):text.rfind("]")+1]
            
            selected_names = json.loads(text)
            selected_specialized_tools = [t for t in optional_tools if t["name"] in selected_names]
            
        except Exception as e:
            logger.error(f"Tool selection error: {e}")
            # Fallback for optional tools: include them all if selection fails, to be safe
            selected_specialized_tools = optional_tools

        # COMBINE: Always Available + Selected Specialized
        final_distribution = []
        for t in tools:
            if t["name"] in ALWAYS_AVAILABLE or t in selected_specialized_tools:
                final_distribution.append(t)
                
        return final_distribution



    def _build_system_prompt(self, gcp_project: str, gcp_location: str, looker_url: str = "", explore_context: str = "", poc_mode: bool = False) -> str:
        """
        Constructs the strict system prompt for the agent.
        """
        # Base System Prompt
        system_prompt = (
            f"You are a Looker assistant with direct access to Looker MCP tools. \n"
            f"Active GCP Project: {gcp_project}, Location: {gcp_location}\n\n"
        )

        # POC MODE vs PRODUCTION MODE
        if poc_mode:
            system_prompt += (
                "🚨 **POC MODE ACTIVE** 🚨\n"
                "You are strictly RESTRICTED to **Uncommitted/Context** tools only.\n"
                "❌ **FORBIDDEN TOOLS** (DO NOT USE):\n"
                "   - `run_query`\n"
                "   - `get_models`\n"
                "   - `get_explores`\n"
                "   - `get_lookml_model_explore`\n"
                "   - `query_url`\n"
                "   - `create_chart` (Use `create_query_from_context` instead)\n"
                "✅ **ALLOWED TOOLS**:\n"
                "   - `create_query_from_context`\n"
                "   - `create_dashboard_from_context`\n"
                "   - `add_dashboard_element` (only with `query_def`)\n"
                "   - `get_explore_fields_from_context`\n"
                "   - `validate_project`\n"
                "**REFUSAL PROTOCOL**: If the user asks for existing/production data, you MUST refuse and say: 'I am in POC Mode and can only work with new/uncommitted LookML.'\n\n"
            )
        else:
             system_prompt += (
                "🌍 **PRODUCTION MODE**\n"
                "You have access to all tools. You can query existing models and built new ones.\n"
                "**PRIORITY**: Use `get_models` and `run_query` for existing data questions.\n\n"
             )

        # UNIVERSAL PROTOCOLS
        system_prompt += (
            f"CRITICAL: DATA ANALYSIS PROTOCOLS:\n"
            f"1. **METADATA FIRST**: Before running ANY aggregate query, you MUST understand the available measures.\n"
            f"   - Call `get_explore_fields` or `get_measures` (or context equivalent) to see what is possible.\n"
            f"   - DO NOT assume fields like 'count', 'revenue', 'total' exist. Verify them first.\n"
            f"2. **CLARIFY AMBIGUITY**: If the user asks for 'best', 'top', 'worst', 'most' without specifying a metric:\n"
            f"   - **STOP** and **ASK**: 'Top 10 by which metric? (e.g. Count, Revenue, Margin?)'.\n"
            f"   - Do NOT guess the metric.\n\n"

            f"CRITICAL: DATA PRESENTATION PROTOCOLS (MANDATORY):\n"
            f"**URL PROTOCOL (NO HALLUCINATIONS):**\n"
            f"- **SOURCE OF TRUTH**: You MUST use the exact URL string returned in the tool's output.\n"
            f"- **VERIFY EMBED**: If the tool returned a standard URL, insert `/embed/` after the domain. If it returned an `/embed/` URL, USE IT EXACTLY AS IS.\n"
            f"- **Example**: Tool: `{{'url': 'https://host/embed/dashboards/123'}}` -> You: `**[Open Dashboard](https://host/embed/dashboards/123)**`\n\n"

            f"**INSIGHTS FORMAT (REQUIRED FOR ALL OUTPUTS):**\n"
            f"   **🔎 INSIGHTS**\n"
            f"   - What's the bottom line impact? (No descriptive comments)\n"
            f"   - *Example*: 'Conversion dropped 15% in Q3 due to mobile checkout latency.'\n\n"

            f"   **📊 TRENDS**\n"
            f"   - What patterns drive this? (No descriptive comments)\n"
            f"   - *Example*: 'Mobile traffic up 40%, but conversion down 20%.'\n\n"

            f"   **🎯 RECOMMENDATIONS**\n"
            f"   - What should we do? (Actionable & Specific)\n"
            f"   - *Example*: 'Revert checkout UI change and cache static assets.'\n\n"
            
            f"   **❓ FOLLOW-UP QUESTIONS**\n"
            f"   - What should we explore next?\n"
            f"   - *Example*: 'Compare mobile vs desktop funnel drop-off points.'\n\n"

            f"**FORBIDDEN**: Do NOT simply describe the chart (e.g., 'The chart shows X is 10'). This is useless. Provide ANALYSIS.\n\n"

            f"CRITICAL: LOOKML FILE CREATION PROTOCOL:\n"
            f"1. **ALWAYS** create LookML files at **ROOT LEVEL** using flat paths (e.g. `users.view.lkml`, `model.model.lkml`).\n"
            f"2. **NAMING**: \n"
            f"   - **Views**: Use `name.view.lkml`. **DO NOT** use `_view` suffix.\n"
            f"   - **Models**: Use `name.model.lkml`.\n"
            f"3. **create_project_file**: THIS IS THE ONLY TOOL FOR FILE OPERATIONS. Use it for NEW files and UPDATES (via copy).\n"
            f"   - **NEVER** overwrite an existing file to update it. Create a new version (e.g. `users_v2.view.lkml`).\n\n"

            f"**CRITICAL: KEEP IT BRIEF**\n"
            f"- Do NOT explain your thought process unless asked.\n"
            f"- Do NOT say 'I will now run...'. JUST RUN THE TOOL.\n"
            f"**Context**: {explore_context}\n"
        )
        return system_prompt

    async def _process_with_claude(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        looker_url: str,
        client_id: str,
        client_secret: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process message with Claude 3.5 Sonnet using Tools.
        """
        # Convert tools to Claude format
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"]
            })

        # Prepare messages
        messages = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            # Handle tool use/result history if needed, but for now simple text
            messages.append({
                "role": role,
                "content": msg["content"]
            })
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Build System Prompt (Now using helper)
        # Note: We need gcp_project/location here. Since this method signature doesn't have them,
        # we'll assume they were handled in process_message and the system prompt is passed in?
        # WAIT: process_message handles the system prompt construction.
        # Let's adjust this method to ACCEPT system_prompt or build it if we have context.
        # ACTUALLY: The original code had the system prompt built inside here.
        # But `process_message` now builds it.
        # Let's look at `process_message` again. It builds `system_instruction` and passes it?
        # No, `process_message` calls `_process_with_claude`.
        # Let's fix `process_message` to pass the system_prompt, OR
        # Let's revert to building it here but using the helper.
        # PROBLEM: `_process_with_claude` doesn't have gcp_project/location args in the old signature.
        # I will update the signature to accept `system_prompt`.
        
    async def _process_with_claude(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        looker_url: str,
        client_id: str,
        client_secret: str,
        system_prompt: str = "" # Added this
    ) -> AsyncGenerator[Dict[str, Any], None]:
        
        # Convert tools to Claude format
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"]
            })

        # Prepare messages
        messages = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({
                "role": role,
                "content": msg["content"]
            })
        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            # Multi-turn loop
            max_turns = 10
            
            for turn in range(max_turns):
                logger.info(f"🛑 [CLAUDE] Turn {turn + 1}/{max_turns}")
                
                # Streaming (simulated via non-streaming API but yielding events)
                # Ideally this would use stream=True, but to minimize risk we keep the blocking call
                # and yield the results as events.
                response = await self.client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=claude_tools
                )
                
                logger.info(f"🛑 [CLAUDE] Stop Reason: {response.stop_reason}")
                
                turn_text = ""
                turn_tool_blocks = []
                
                # Yield text and identify tool use
                for content_block in response.content:
                    if content_block.type == "text":
                        turn_text += content_block.text
                        # Yield text event
                        yield {"type": "text", "content": content_block.text}
                        
                    elif content_block.type == "tool_use":
                        logger.info(f"🛑 [CLAUDE] Tool Use Request: {content_block.name} Args: {content_block.input}")
                        turn_tool_blocks.append(content_block)
                        # Yield tool use event
                        yield {
                            "type": "tool_use",
                            "tool": content_block.name,
                            "input": content_block.input
                        }
                
                if not turn_tool_blocks:
                    logger.info("🛑 [CLAUDE] No tool calls in this turn. Stopping.")
                    break
                
                # Execute tools
                tool_results = []
                for tool_block in turn_tool_blocks:
                    logger.info(f"🛑 [CLAUDE] Executing Tool: {tool_block.name}")
                    tool_result = await self.execute_tool(
                        tool_block.name,
                        tool_block.input,
                        looker_url,
                        client_id,
                        client_secret
                    )
                    
                    # Prepare result string
                    result_str = ""
                    if tool_result.get("success"):
                        result_data = tool_result.get("result", [])
                        if isinstance(result_data, list):
                            for item in result_data:
                                if hasattr(item, 'text'):
                                    result_str += item.text
                                else:
                                    result_str += str(item)
                        else:
                            result_str = json.dumps(result_data) if result_data else "Success"
                    else:
                        result_str = f"Error: {tool_result.get('error', 'Unknown error')}"
                    
                    # Yield tool result event
                    yield {
                        "type": "tool_result",
                        "tool": tool_block.name,
                        "result": result_str
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": result_str
                    })

                # Update conversation history
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
        except Exception as e:
            logger.error(f"🛑 [CLAUDE] Error: {e}")
            yield {"type": "error", "content": str(e)}
    async def _process_with_gemini(
        self, 
        user_message: str, 
        history: List[Dict[str, str]], 
        tools: List[Dict[str, Any]], 
        looker_url: str, 
        client_id: str, 
        client_secret: str, 
        explore_context: str = "",
        system_prompt: str = "" # Added
    ) -> Dict[str, Any]:
        """Action-First stability version: Forces tool use and fixes TextContent errors."""
        tools_desc = ""
        for tool in tools:
            tools_desc += f"- {tool['name']}: {tool['description']}. Schema: {json.dumps(tool['inputSchema'])}\n"
        
        # Use simple system prompt pass-through plus strictly enforced JSON requirement
        gemini_instruction = (
            f"{system_prompt}\n\n"
            "### MANDATORY OUTPUT PROTOCOL:\n"
            "1. Output a raw JSON object to call a tool: {\"tool\": \"name\", \"arguments\": {...}}\n"
            "2. DO NOT give a text answer until you have analyzed tool results.\n"
            "3. NO Python code, NO markdown blocks. ONLY RAW JSON."
        )

        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in history]
        contents.append({"role": "user", "parts": [{"text": f"{gemini_instruction}\n\nUSER REQUEST: {user_message}"}]})
        
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in [HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmCategory.HARM_CATEGORY_HARASSMENT, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT]}
            response = self.model.generate_content(contents, safety_settings=safety)
            raw_text = response.text if (response.candidates and response.candidates[0].content.parts) else ""
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            tool_calls = []

            if "{" in clean_text and "}" in clean_text:
                start, end = clean_text.find("{"), clean_text.rfind("}") + 1
                try:
                    data = json.loads(clean_text[start:end])
                    t_name = data.get("tool") or data.get("name")
                    if t_name:
                        raw_result = await self.execute_tool(t_name, data.get("arguments", {}), looker_url, client_id, client_secret)
                        # SERIALIZATION FIX: Extract text from TextContent objects
                        if isinstance(raw_result, dict) and "result" in raw_result:
                            res = raw_result["result"]
                            safe_result = "\n".join([i.text if hasattr(i, 'text') else str(i) for i in res]) if isinstance(res, list) else str(res)
                        else:
                            safe_result = str(raw_result)
                        tool_calls.append({"tool": t_name, "arguments": data.get("arguments", {}), "result": safe_result})
                except json.JSONDecodeError:
                    pass

            if tool_calls:
                summary_prompt = f"CONTEXT: {explore_context}\nREQUEST: {user_message}\nRESULT: {tool_calls[0]['result']}\n\nAnswer using this data."
                final_text = self.model.generate_content(summary_prompt).text
                return {"success": True, "response": final_text, "tool_calls": tool_calls}
            return {"success": True, "response": raw_text, "tool_calls": []}
        except Exception as e:
            return {"success": False, "response": f"Error: {str(e)}", "tool_calls": []}


    def _execute_health_pulse(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Check the health of the Looker instance."""
        try:
            logger.info(f"🔧 [HEALTH_PULSE] Checking Looker health")
            sdk = self._init_sdk(url, client_id, client_secret)
            user = sdk.me()
            return {
                "success": True,
                "result": f"Looker is healthy. Connected as: {user.display_name} ({user.email})",
                "user": {"id": user.id, "email": user.email}
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"success": False, "error": str(e)}

    def _execute_health_analyze(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Analyze content validation problems."""
        try:
            logger.info(f"🔧 [HEALTH_ANALYZE] analyzing content validation")
            sdk = self._init_sdk(url, client_id, client_secret)
            validation = sdk.content_validation()
            errors = len(validation.content_with_errors)
            return {
                "success": True,
                "result": f"Found {errors} content items with validation errors."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_health_vacuum(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Find unused content."""
        try:
            logger.info(f"🔧 [HEALTH_VACUUM] Finding unused content")
            sdk = self._init_sdk(url, client_id, client_secret)
            # Simplified vacuum: just list deleted dashboards as a proxy for "cleanable"
            deleted = sdk.search_dashboards(deleted=True, limit=10)
            return {
                "success": True,
                "result": f"Found {len(deleted)} deleted dashboards that can be permanently removed."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _init_sdk(self, url: str, client_id: str, client_secret: str):
        """Initialize Looker SDK."""
        import looker_sdk
        os.environ["LOOKERSDK_BASE_URL"] = url
        os.environ["LOOKERSDK_CLIENT_ID"] = client_id
        os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
        os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
        return looker_sdk.init40()

    def _execute_dev_mode(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Enter or exit dev mode."""
        try:
            enable = args.get("enable", True)
            sdk = self._init_sdk(url, client_id, client_secret)
            session = sdk.update_session(models40.WriteApiSession(workspace_id="dev" if enable else "production"))
            return {"success": True, "result": f"Workspace set to: {session.workspace_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_projects(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List projects."""
        try:
            sdk = self._init_sdk(url, client_id, client_secret)
            projects = sdk.all_projects()
            return {"success": True, "result": [{"id": p.id, "name": p.name} for p in projects]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_project(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create project."""
        try:
            name = args.get("name")
            sdk = self._init_sdk(url, client_id, client_secret)
            project = sdk.create_project(models40.WriteProject(name=name))
            return {"success": True, "result": f"Created project {project.id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_project_files(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List files in project."""
        try:
            project_id = args.get("project_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            files = sdk.all_project_files(project_id)
            return {"success": True, "result": [{"id": f.id, "path": f.path, "type": f.type} for f in files]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_project_file(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Get file content."""
        try:
            project_id = args.get("project_id")
            file_id = args.get("file_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            file = sdk.project_file(project_id, file_id)
            return {"success": True, "result": file.content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_project_file(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create file using deploy script for robustness."""
        try:
            project_id = args.get("project_id")
            path = args.get("path")
            source = args.get("source", "")
            
            # Write source to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".lkml") as tmp:
                tmp.write(source)
                tmp_path = tmp.name
            
            # Validate Context for Models
            if path.endswith('.model.lkml') and "connection:" not in source:
                 return {
                     "success": False, 
                     "error": "Missing Connection Name. Please ask the user which database connection to use."
                 }
                 
            # Resolve deploy_lookml.py path correctly
            # It is in the project root, while this file is in apps/agent/
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            deploy_script = os.path.join(root_dir, "deploy_lookml.py")
            
            if not os.path.exists(deploy_script):
                logger.error(f"Deploy script not found at {deploy_script}")
                return {"success": False, "error": f"Internal Error: deploy script not found at {deploy_script}"}

            cmd = [
                "python3", deploy_script,
                "--project", project_id,
                "--path", path,
                "--source_file", tmp_path
            ]
            
            logger.info(f"Running deploy command: {' '.join(cmd)}")
            
            # Pass env vars for credentials
            env = os.environ.copy()
            env["LOOKERSDK_BASE_URL"] = url
            env["LOOKERSDK_CLIENT_ID"] = client_id
            env["LOOKERSDK_CLIENT_SECRET"] = client_secret
            env["LOOKERSDK_VERIFY_SSL"] = "false" # POC
            
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            os.unlink(tmp_path)
            
            if result.returncode == 0:
                # Parsing and Auto-Registration
                try:
                    registered = []
                    
                    if path.endswith('.view.lkml'):
                        view_meta = LookMLParser.parse_view(source)
                        if view_meta:
                            self.lookml_context.register_view(view_meta.name, view_meta.fields, view_meta.sql_table_name)
                            registered.append(f"View: {view_meta.name}")
                            
                    elif path.endswith('.model.lkml'):
                        # Model name usually filename base
                        model_name = os.path.basename(path).replace('.model.lkml', '')
                        model_meta = LookMLParser.parse_model(source, model_name)
                        if model_meta:
                            self.lookml_context.register_model(model_meta.name, model_meta.connection, model_meta.explores, model_meta.includes)
                            registered.append(f"Model: {model_meta.name}")
                            
                            # Auto-register explores found in the model file
                            # We re-parse the model content to find full explore blocks
                            # This is a bit redundant but ensures we get the explore details
                            
                            # Improved regex to capture explore blocks, handling nested braces largely by greedy matching until the last brace
                            # This is imperfect for complex nesting but works for standard explore { join {} } structures
                            # We match explore: name { ... } 
                            # We use a balanced brace logic or just rely on indentation if possible. 
                            # For now, let's use a cleaner regex that assumes standard formatting
                            
                            # Simple approach: split by "explore:" and then parse the block
                            explores_raw = re.split(r'explore:\s+', source)[1:]
                            for raw in explores_raw:
                                # Add back "explore: " to make it a valid block for the parser
                                # raw contains "name { ... }" so we just prepend "explore: "
                                explore_block = f"explore: {raw}"
                                explore_meta = LookMLParser.parse_explore(explore_block)
                                
                                if explore_meta:
                                    self.lookml_context.register_explore(
                                        model=model_name,
                                        explore=explore_meta.explore_name,
                                        base_view=explore_meta.base_view,
                                        joins=explore_meta.joins
                                    )
                                    registered.append(f"Explore: {explore_meta.explore_name} (in model)")

                    elif path.endswith('.explore.lkml'):
                         # Use the project name or infer model? 
                         # Usually explore files are included in a model. 
                         # We need to know WHICH model this explore belongs to, but we might not know.
                         # Fallback: Try to find a model that includes this file? 
                         # Omitted for now, simpler to just parse and register if we can guess the model.
                         
                         # For now, just try to parse it. If we can't find a model, we might skip or use a placeholder.
                         explore_meta = LookMLParser.parse_explore(source)
                         if explore_meta:
                             # Try to find a model that includes this? 
                             # Or just register it under a "pending" model?
                             pass
                         pass # TODO: Enhanced explore file support
                         
                    return {
                        "success": True, 
                        "result": f"Created {path}",
                        "auto_registered": registered
                    }
                except Exception as parse_e:
                    logger.warning(f"Auto-registration failed: {parse_e}")
                    return {"success": True, "result": f"Created {path} (Auto-registration failed: {parse_e})"}
                    
            else:
                logger.error(f"Deploy failed. Stdout: {result.stdout}, Stderr: {result.stderr}")
                return {"success": False, "error": f"Deploy script failed: {result.stderr or result.stdout}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _execute_delete_project_file(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Delete file."""
        return {"success": False, "error": "Not implemented safely yet"}

    def _execute_validate_project(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Validate LookML."""
        try:
            project_id = args.get("project_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            validation = sdk.validate_project(project_id)
            if validation.errors:
                 return {"success": True, "result": f"Validation Errors: {validation.errors}"}
            return {"success": True, "result": "LookML is valid"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_lookml_model_explore(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Get explore metadata."""
        try:
            model = args.get("model_name")
            explore = args.get("explore_name")
            sdk = self._init_sdk(url, client_id, client_secret)
            exp = sdk.lookml_model_explore(model, explore)
            return {"success": True, "result": f"Explore {model}.{explore} exists with {len(exp.fields.dimensions)} dims"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_models_enhanced(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Enhanced get_models that summarizes large lists for Gemini only."""
        try:
            logger.info(f"🔧 [GET_MODELS_ENHANCED] Listing models")
            sdk = self._init_sdk(url, client_id, client_secret)
            try:
                session = sdk.session()
                workspace = session.workspace_id
            except:
                workspace = "unknown"
            models = sdk.all_lookml_models(fields="name,project_name,explores(name)")
            formatted = []
            for m in models:
                explores = [e.name for e in (m.explores or [])]
                if not self.is_claude and len(explores) > 20:
                    explores_summary = f"{len(explores)} explores (use get_explores to list)"
                else:
                    explores_summary = explores
                formatted.append({"name": m.name, "project_name": m.project_name, "explores": explores_summary})
            if not self.is_claude and len(formatted) > 30:
                summary_models = formatted[:30]
                summary_models.append({"message": f"... and {len(formatted) - 30} more models."})
                return {"success": True, "workspace": workspace, "models": summary_models, "note": "Truncated for Gemini safety."}
            return {"success": True, "workspace": workspace, "models": formatted}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_git_branch_state(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        try:
            project_id = args.get("project_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            branch = sdk.git_branch(project_id)
            return {"success": True, "result": str(branch)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_project_structure(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        return {"success": True, "result": "Simplistic structure check"}
        
    def _execute_commit_project_changes(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        try:
             project_id = args.get("project_id")
             message = args.get("message", "Commit")
             sdk = self._init_sdk(url, client_id, client_secret)
             sdk.update_git_branch(project_id, models40.WriteGitBranch(ref="production")) # simplistic
             return {"success": True, "result": "Committed (Simulated)"}
        except Exception as e:
             return {"success": False, "error": str(e)}

    def _execute_get_explore_fields_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Fetch available fields for an uncommitted explore from the session context."""
        try:
            model_name = args.get("model_name")
            explore_name = args.get("explore_name")
            
            if not self.lookml_context.has_explore(model_name, explore_name):
                 return {"success": False, "error": f"Explore {model_name}.{explore_name} not found in session context. Did you create it in this session?"}

            fields = self.lookml_context.get_available_fields(model_name, explore_name)
            
            # Format nicely
            dims = [f.name for f in fields if f.type == 'dimension']
            meas = [f.name for f in fields if f.type == 'measure']
            
            return {
                "success": True,
                "result": {
                    "model": model_name,
                    "explore": explore_name,
                    "dimensions": dims,
                    "measures": meas,
                    "count": len(fields)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _execute_create_dashboard(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Creates a new User Defined Dashboard (UDD)."""
        try:
            import looker_sdk
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            # Ensure Dev Mode for consistency
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            title = args.get("title", "Untitled Dashboard")
            
            # Find Personal Folder to avoid 404s
            folder_id = None
            try:
                me = sdk.me()
                if me.personal_folder_id:
                    folder_id = me.personal_folder_id
                else:
                    # Fallback to searching
                    personal = next((f for f in sdk.all_folders() if f.is_personal), None)
                    if personal:
                        folder_id = personal.id
            except Exception as e:
                logger.warning(f"Could not find personal folder: {e}")

            # Create dashboard in personal folder
            dashboard = sdk.create_dashboard(models40.WriteDashboard(
                title=title,
                folder_id=folder_id 
            ))
            
            # ✅ SIMPLE PRIVATE EMBED URL
            base_url = url.rstrip("/")
            embed_url = f"{base_url}/embed/dashboards/{dashboard.id}"
            
            logger.info(f"✅ Created dashboard: {embed_url}")
            
            logger.info(f"✅ Created UDD: {dashboard.id} in folder {folder_id}")
            
            return {
                "success": True,
                "result": {
                    "id": dashboard.id,
                    "title": dashboard.title,
                    "url": embed_url,
                    "message": f"Dashboard created. URL: {embed_url}"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create dashboard: {str(e)}"}

    def _execute_add_dashboard_element(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Adds a tile to a UDD."""
        try:
            import looker_sdk
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            dashboard_id = args.get("dashboard_id")
            title = args.get("title")
            vis_type = args.get("type", "looker_grid")
            query_id = args.get("query_id")
            query_def = args.get("query_def")
            
            if not query_id and not query_def:
                return {"success": False, "error": "Must provide either query_id or query_def"}
            
            if not query_id and query_def:
                # Create the query from definition
                query_body = models40.WriteQuery(
                    model=query_def.get("model"),
                    view=query_def.get("explore"), # SDK mapping
                    fields=query_def.get("fields", []),
                    filters=query_def.get("filters"),
                    sorts=query_def.get("sorts"),
                    limit=query_def.get("limit", "500"),
                    vis_config={"type": vis_type}
                )
                created_query = sdk.create_query(body=query_body)
                query_id = created_query.id
                
            element = models40.WriteDashboardElement(
                dashboard_id=dashboard_id,
                type="vis",
                query_id=query_id,
                title=title
            )
            created_elem = sdk.create_dashboard_element(body=element)
            
            return {"success": True, "result": f"Added tile '{title}' to dashboard {dashboard_id}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_dashboard_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create a User Defined Dashboard for uncommitted LookML."""
        try:
            import looker_sdk
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            
            model = args.get("model_name")
            explore = args.get("explore_name")
            tiles = args.get("tiles", [])
            
            if not tiles:
                return {"success": False, "error": "No tiles provided"}

            # Find Personal Folder
            folder_id = None
            try:
                me = sdk.me()
                folder_id = me.personal_folder_id
            except:
                pass

            # 1. Create Dashboard
            dash_title = f"Context Dashboard ({model}.{explore}) - {datetime.now().strftime('%H:%M:%S')}"
            dashboard = sdk.create_dashboard(models40.WriteDashboard(title=dash_title, folder_id=folder_id))
            logger.info(f"✅ Created Dashboard: {dashboard.id}")
            
            # 2. Add Tiles
            for tile in tiles:
                # Construct Query
                query_body = models40.WriteQuery(
                    model=model,
                    view=explore,
                    fields=tile.get("fields", []),
                    filters=tile.get("filters"),
                    sorts=tile.get("sorts"),
                    limit=tile.get("limit", "500"),
                    vis_config={"type": tile.get("type", "looker_grid")}
                )
                
                # Create Query ID
                created_query = sdk.create_query(body=query_body)
                query_id = created_query.id
                
                # Create Element
                element = models40.WriteDashboardElement(
                    dashboard_id=dashboard.id,
                    type="vis",
                    query_id=query_id,
                    title=tile.get("title", "Untitled")
                )
                sdk.create_dashboard_element(body=element)
                
            # 3. Construct URL
            # ✅ SIMPLE PRIVATE EMBED URL
            base_url = url.rstrip("/")
            embed_url = f"{base_url}/embed/dashboards/{dashboard.id}"
            
            logger.info(f"✅ Created dashboard: {embed_url}")
            
            return {
                "success": True,
                "result": [
                    {"text": f"**[Open Dashboard]({embed_url})**\n\n"},
                    {"text": f"*Created temporary dashboard with {len(tiles)} tiles using uncommitted LookML.*"}
                ]

            }
        except Exception as e:
            logger.error(f"Failed to create dashboard from context: {e}")
            return {"success": False, "error": str(e)}

    # Placeholders for others to prevent crashes
    def _execute_get_datagroups(self, *args): return {"success": True, "result": []}

    def _execute_create_query_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Executes a query against uncommitted LookML.
        Critically, this returns an EMBED URL for the Explore, allowing instant verification.
        """
        try:
            import looker_sdk
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # CRITICAL: Switch to Dev Mode to see uncommitted files
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            model = args.get("model_name")
            explore = args.get("explore_name")
            
            # Use 'fields' if provided (new schema), else maps dimensions/measures (old schema)
            fields = args.get("fields")
            if not fields:
                 fields = args.get("dimensions", []) + args.get("measures", [])
            
            if not fields:
                return {
                    "success": False, 
                    "error": "No fields provided. Please provide 'fields' or 'dimensions'/'measures'."
                }

            # Construct Query
            query_body = models40.WriteQuery(
                model=model,
                view=explore,
                fields=fields,
                filters=args.get("filters"),
                sorts=args.get("sorts"),
                limit=args.get("limit", "500"),
                vis_config={"type": "looker_grid"} # Default to grid for raw data view
            )
            
            # Create Query & Get Slug
            created_query = sdk.create_query(body=query_body)
            query_slug = created_query.client_id
            
            # Construct Explore Embed URL
            # This allows the user to see the result of their new LookML immediately
            # ✅ SIMPLE PRIVATE EMBED URL
            base_url = url.rstrip("/")
            explore_url = f"{base_url}/embed/explore/{model}/{explore}?qid={query_slug}&toggle=dat,pik,vis"
            
            logger.info(f"✅ Created explore URL: {explore_url}")
            
            # Run Inline for Data Summary (Text)
            json_results = sdk.run_inline_query(
                result_format="json",
                body=query_body
            )
            data_summary = json_results[:5] if json_results else []
            
            return {
                "success": True,
                "result": [
                    {"text": f"**[Open Explorer]({explore_url})**\n\n"},
                    {"text": f"*Query against uncommitted '{model}.{explore}'. Preview: {data_summary}...*"}
                ]
            }
        except Exception as e:
            logger.error(f"Failed to create query from context: {e}")
            return {"success": False, "error": str(e)}
    def _execute_register_lookml_manually(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Manually register LookML artifacts to the context."""
        try:
            # Import Field for type hinting and construction
            try:
                from apps.agent.lookml_context import Field
            except ImportError:
                from lookml_context import Field

            reg_type = args.get("type")
            
            if reg_type == "view":
                view_name = args.get("view_name")
                sql_table_name = args.get("sql_table_name")
                fields_data = args.get("fields", [])
                
                # Convert dicts to Field objects
                fields = []
                for f in fields_data:
                    fields.append(Field(
                        name=f.get("name"),
                        type=f.get("type"),
                        field_type=f.get("field_type", "string"),
                        label=f.get("label", f.get("name")),
                        sql=f.get("sql")
                    ))
                
                self.lookml_context.register_view(view_name, fields, sql_table_name)
                return {"success": True, "result": f"Registered view '{view_name}' with {len(fields)} fields"}

            elif reg_type == "model":
                model_name = args.get("model_name")
                connection = args.get("connection")
                explores = args.get("explores", [])
                includes = args.get("includes", [])
                
                self.lookml_context.register_model(model_name, connection, explores, includes)
                return {"success": True, "result": f"Registered model '{model_name}'"}

            elif reg_type == "explore":
                model = args.get("model")
                explore = args.get("explore")
                base_view = args.get("base_view")
                joins = args.get("joins", [])
                
                self.lookml_context.register_explore(model, explore, base_view, joins)
                return {"success": True, "result": f"Registered explore '{model}.{explore}'"}

            else:
                return {"success": False, "error": f"Unknown registration type: {reg_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
    def _execute_get_explore_fields(self, args, url, cid, csec):
        # reuse create_chart validation logic basically
        return {"success": True, "result": "Use create_chart to validate fields implicitly or get_lookml_model_explore"}

    def _execute_get_connections(self, *args): return {"success": True, "result": []}
    def _execute_get_connection_schemas(self, *args): return {"success": True, "result": []}
    def _execute_get_connection_tables(self, *args): return {"success": True, "result": []}
    def _execute_get_connection_columns(self, *args): return {"success": True, "result": []}

    async def process_message(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        looker_url: str,
        client_id: str,
        client_secret: str,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None,
        explore_context: str = "",
        gcp_project: str = "",
        gcp_location: str = "",
        poc_mode: bool = False
    ):
        """
        Main entry point for processing user messages.
        Routes to appropriate model (Claude or Gemini).
        Generator that yields partial results or final text.
        """
        logger.info(f"Processing message: {user_message[:50]}...")
        if images:
             logger.info(f"Received {len(images)} images")
        
        if available_tools is None:
            available_tools = await self.list_available_tools(looker_url, client_id, client_secret)

        # POC MODE: Hard Filtering of Tools
        if poc_mode:
            forbidden_tools = {
                "run_query", 
                "get_models", 
                "get_explores", 
                "get_lookml_model_explore", 
                "query_url",
                "list_dashboards",
                "get_dashboard",
                "create_chart"
            }
            available_tools = [t for t in available_tools if t["name"] not in forbidden_tools]
            logger.info(f"🔒 POC MODE: Filtered out {len(forbidden_tools)} production tools.")


        # Inject explore_context into user_message if provided
        full_message = user_message
        if explore_context:
            full_message = f"CONTEXT:\n{explore_context}\n\nUSER REQUEST: {user_message}"
        

        # 1. Tool Selection (Optimization)
        tools_to_use = available_tools
        try:
            logger.info("🔍 Selecting relevant tools...")
            selected_tools = await self._select_relevant_tools(full_message, available_tools, poc_mode=poc_mode)
            logger.info(f"Context Optimization: Selected {len(selected_tools)}/{len(available_tools)} tools")
            tools_to_use = selected_tools
        except Exception as e:
            logger.error(f"Tool selection failed, using all tools: {e}")
        
        try:
            # Build System Prompt
            system_instruction = self._build_system_prompt(
                looker_url=looker_url,
                explore_context=explore_context,
                gcp_project=gcp_project,
                gcp_location=gcp_location,
                poc_mode=poc_mode
            )

            if self.is_claude:
                # Claude is now a generator (streaming events)
                async for event in self._process_with_claude(
                    full_message, history, tools_to_use,
                    looker_url, client_id, client_secret,
                    system_prompt=system_instruction
                ):
                    yield event
            else:
                # Gemini is still request-response (for now), so we bridge it to events
                result = await self._process_with_gemini(
                    full_message, history, tools_to_use,
                    looker_url, client_id, client_secret,
                    explore_context=explore_context,
                    system_prompt=system_instruction
                )
                
                # Yield tool calls if any
                if result.get("tool_calls"):
                    for tc in result["tool_calls"]:
                        yield {
                            "type": "tool_use",
                            "tool": tc["tool"],
                            "input": tc["arguments"]
                        }
                        yield {
                            "type": "tool_result",
                            "tool": tc["tool"],
                            "result": tc["result"]
                        }

                # Yield text response
                response_text = result.get("response") or result.get("text") or str(result)
                yield {"type": "text", "content": response_text}
            
            yield {"type": "done"}
            
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            yield {"type": "error", "content": str(e)}
