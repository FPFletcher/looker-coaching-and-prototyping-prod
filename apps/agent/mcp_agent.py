import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
import google.generativeai as genai
from anthropic import AsyncAnthropic
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from duckduckgo_search import DDGS
import base64
import requests
import re
import html
import google.auth
import google.auth.transport.requests
from datetime import datetime
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Import and initialize LookML context tracking (Global Singleton)
try:
    from apps.agent.lookml_context import LookMLContext, LookMLParser, Field
except ImportError:
    try:
        from lookml_context import LookMLContext, LookMLParser, Field
    except ImportError:
        logger.warning("Could not import LookMLContext. Context features will be disabled.")
        LookMLContext = None
        LookMLParser = None
        Field = None

# Initialize global context - REMOVED for Session Isolation
# GLOBAL_LOOKML_CONTEXT = LookMLContext() if LookMLContext else None
# if GLOBAL_LOOKML_CONTEXT:
#     GLOBAL_LOOKML_CONTEXT.load_from_file()

# ==========================================
# POC MODE CONFIGURATION
# ==========================================

# Tools that are ESSENTIAL for POC mode (creating uncommitted LookML + visualization)
# Philosophy: POC mode = "Build new LookML, visualize it, iterate"
POC_SAFE_TOOLS = {
    # Core LookML Creation Workflow
    "create_project_file",      # Create views/models/explores
    "get_project_files",        # List files (also reads single file if path provided)
    "dev_mode",                 # Required to see uncommitted changes
    "validate_project",         # Check LookML syntax
    "get_git_branch_state",     # See uncommitted changes
    
    # Context Management (auto-registration fallback)
    "get_explore_fields_from_context",  # Validate fields before querying
    "register_lookml_manually",         # Manual registration if auto fails
    
    # Visualization (uncommitted LookML)
    "create_chart_from_context",        # Single visual - PRIORITIZE THIS
    "create_dashboard",                 # Multi-tile: Step 1
    "add_dashboard_element",            # Multi-tile: Step 2
    "create_dashboard_filter",          # Add filters to dashboards
    
    # Database Discovery (for building LookML from scratch)
    "get_connections",                  # List available connections
    "get_connection_schemas",           # Browse database structure
    "get_connection_tables",            # Find tables to model
    "get_connection_columns",           # Get column details
    
    # Utility
    "search_web",                       # External context/research
    "read_url_content",                 # Read website content
    "deep_search",                      # Search + Read content
    "check_internet_connection"         # Health check
}

# Tools that require PRODUCTION/COMMITTED LookML (forbidden in POC mode)
PRODUCTION_ONLY_TOOLS = {
    # Query Execution (requires committed LookML)
    "run_query",
    "query_url",
    "create_chart",  # Production version
    
    # Model/Explore Discovery (only shows committed content)
    "get_models",
    "get_explores", 
    "get_lookml_model_explore",
    "get_dimensions",
    "get_measures",
    "get_filters",
    "get_parameters",
    
    # Content Management (production assets)
    "run_look",
    "get_looks",
    "run_dashboard",
    "get_dashboards",
    
    # Project Management (not needed for POC iteration)
    "get_projects",              # List all projects
    "create_project",            # Create new project
    "delete_project_file",       # Destructive operation
    "get_project_structure",     # Analysis tool
    "commit_project_changes",    # Deployment operation
    
    # Advanced Features (not POC-critical)
    "get_datagroups",            # Cache management
    "list_data_agents",          # GCP-specific
    "chat_with_data_agent",      # GCP-specific
    "health_pulse",              # Instance monitoring
    "health_analyze",            # Content validation
    "health_vacuum"              # Cleanup tool
}

# ==========================================
# AGENT CLASS
# ==========================================

class MCPAgent:
    """
    Conversational agent that uses Gemini or Claude to interpret user requests
    and executes appropriate Looker MCP tools.
    
    Supports both POC mode (uncommitted LookML only) and Production mode.
    """
    
    def __init__(self, session_id: str = "default", model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.session_id = session_id
        self.created_files_cache = {}
        
        # Initialize session-specific context
        if LookMLContext:
            self.lookml_context = LookMLContext(session_id)
            self.lookml_context.load_from_file()
        else:
            self.lookml_context = None
        
        self.is_claude = model_name.startswith("claude-")
        
        if self.is_claude:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise Exception("ANTHROPIC_API_KEY not found in environment")
            
            # Configure extended timeouts to prevent 60s read timeout from killing long requests
            self.client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                timeout=httpx.Timeout(
                    connect=10.0,    # Connection timeout
                    read=600.0,      # Read timeout - 10 minutes (was 60s default)
                    write=10.0,      # Write timeout
                    pool=10.0        # Pool timeout
                )
            )
        else:
            if not os.getenv("GOOGLE_API_KEY"):
                raise Exception("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = genai.GenerativeModel(model_name)
        
        # Path to MCP toolbox binary
        self.toolbox_bin = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../tools/mcp-toolbox/toolbox"
        ))
        
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
    
    def _init_sdk(self, url: str, client_id: str, client_secret: str):
        """Initialize Looker SDK for custom tool implementations."""
        import looker_sdk
        os.environ["LOOKERSDK_BASE_URL"] = url
        os.environ["LOOKERSDK_CLIENT_ID"] = client_id
        os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
        os.environ["LOOKERSDK_VERIFY_SSL"] = "true"
        return looker_sdk.init40()
    
    # ==========================================
    # TOOL LISTING
    # ==========================================
    
    async def list_available_tools(
        self, 
        looker_url: str, 
        client_id: str, 
        client_secret: str,
        poc_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Lists all available Looker MCP tools.
        
        In POC mode: Returns only tools that work with uncommitted LookML.
        In Production mode: Returns all tools.
        
        Returns tool names, descriptions, and schemas.
        """
        # Sanitize looker_url
        if looker_url and not looker_url.startswith(("http://", "https://")):
             looker_url = f"https://{looker_url}"

        logger.info(f"Listing tools (POC Mode: {poc_mode})...")
        
        tools = []
        
        # ===========================================
        # SECTION 1: CUSTOM PYTHON IMPLEMENTATIONS
        # ===========================================
        # These are implemented in Python for better control and work with uncommitted LookML
        
        if poc_mode:
            # --- File Operations ---
            
            tools.append({
                "name": "create_project_file",
                "description": "Creates and auto-registers a new file in a project. REQUIRED context for models: connection name. Auto-registers views/models/explores in session. WORKS WITH UNCOMMITTED LOOKML.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "path": {"type": "string", "description": "File path (e.g. views/users.view.lkml)"},
                        "source": {"type": "string", "description": "File content"}
                    },
                    "required": ["project_id", "path", "source"]
                }
            })
            
            tools.append({
                "name": "get_project_files",
                "description": "List files in a LookML project. Can also read a specific file by providing file_id parameter.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "file_id": {"type": "string", "description": "Optional: specific file path to read (e.g. 'views/users.view.lkml')"}
                    },
                    "required": ["project_id"]
                }
            })
            
            # --- LookML Management ---
            
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
                "name": "validate_project",
                "description": "Validates LookML syntax in a project and returns any errors. Call this after creating/updating LookML files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID to validate"}
                    },
                    "required": ["project_id"]
                }
            })
            
            tools.append({
                "name": "get_git_branch_state",
                "description": "Get git branch state including uncommitted changes. Critical for finding newly created LookML files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"}
                    },
                    "required": ["project_id"]
                }
            })
            
            # --- Context Management ---

            tools.append({
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
            })
            
            tools.append({
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
            })
            
            # --- Visualization Tools (POC-safe) ---
            
            tools.append({
                "name": "create_chart_from_context",
                "description": "Generate a SINGLE chart/visualization for uncommitted LookML. Use this for simple single-visual questions in POC mode.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "explore_name": {"type": "string"},
                        "fields": {"type": "array", "items": {"type": "string"}, "description": "List of fields (dimensions/measures)"},
                        "filters": {"type": "object", "description": "Dictionary where keys are field names and values are filter expressions"},
                        "sorts": {"type": "array", "items": {"type": "string"}, "description": "List of fields to sort by"},
                        "limit": {"type": "string", "description": "Row limit (default 500)"},
                        "vis_type": {"type": "string", "description": "Visualization type (looker_line, looker_column, looker_grid, looker_pie)"}
                    },
                    "required": ["model_name", "explore_name", "fields"]
                }
            })
        
        tools.append({
            "name": "create_dashboard",
            "description": "STEP 1 of dashboard creation: Create a new empty User Defined Dashboard. Returns dashboard_id and base_url. In POC mode, use for multi-tile uncommitted LookML dashboards. ALWAYS save the returned dashboard_id and base_url for subsequent add_dashboard_element calls.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the dashboard"}
                },
                "required": ["title"]
            }
        })
        
        tools.append({
            "name": "add_dashboard_element",
            "description": "STEP 2 of dashboard creation: Add a tile to an existing dashboard. MUST use dashboard_id from create_dashboard output. For POC mode, use query_def to work with uncommitted LookML.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dashboard_id": {"type": "string", "description": "ID from create_dashboard output - NEVER invent this"},
                    "title": {"type": "string", "description": "Title of the tile"},
                    "type": {"type": "string", "description": "Visualization type (looker_grid, looker_column, etc.)"},
                    "query_id": {"type": "string", "description": "Optional: Existing query ID (production mode only)"},
                    "query_def": {
                        "type": "object",
                        "description": "Define a new query inline (use this for POC mode/uncommitted LookML)",
                        "properties": {
                            "model": {"type": "string"},
                            "explore": {"type": "string"},
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
        })
        
        tools.append({
            "name": "create_dashboard_filter",
            "description": "Add a filter to an existing dashboard. Types: field_filter, date_filter, string_filter, number_filter.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dashboard_id": {"type": "string", "description": "ID of the dashboard"},
                    "name": {"type": "string", "description": "Name of the filter (internal)"},
                    "title": {"type": "string", "description": "Display title for the filter"},
                    "type": {"type": "string", "description": "Type of filter"},
                    "model": {"type": "string", "description": "Model name"},
                    "explore": {"type": "string", "description": "Explore name"},
                    "dimension": {"type": "string", "description": "Fully qualified dimension name"}
                },
                "required": ["dashboard_id", "title", "type", "model", "explore", "dimension"]
            }
        })
        
        # --- Utility Tools ---
        
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
            "name": "read_url_content",
            "description": "Read and extract text content from a specific URL.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to read"}
                },
                "required": ["url"]
            }
        })

        tools.append({
            "name": "deep_search",
            "description": "Perform a deep search: searches the web AND reads the content of the top results.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Number of results to read (default 3, max 5)"}
                },
                "required": ["query"]
            }
        })

        tools.append({
            "name": "check_internet_connection",
            "description": "Check if the agent has active internet connectivity. Use this if web searches fail.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        })
        
        # --- Database Metadata Tools (helpful for LookML creation) ---
        
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
        
        # ===========================================
        # SECTION 2: BINARY TOOLS (from MCP toolbox)
        # ===========================================
        # These come from the binary and may require production/committed LookML
        
        server_params = self._get_server_params(looker_url, client_id, client_secret)
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    # Track which tools we've manually defined above
                    manual_tool_names = {t["name"] for t in tools}
                    
                    for tool in tools_result.tools:
                        # Skip tools we've already defined manually
                        if tool.name in manual_tool_names:
                            continue
                        
                        # In POC mode, skip production-only tools
                        if poc_mode and tool.name in PRODUCTION_ONLY_TOOLS:
                            logger.info(f"Skipping production-only tool in POC mode: {tool.name}")
                            continue
                        
                        # Add the tool
                        tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        })
                        
        except Exception as e:
            logger.warning(f"Binary tool listing failed (non-fatal): {e}")
        
        # ===========================================
        # SECTION 3: PRODUCTION MODE ENHANCEMENTS
        # ===========================================
        # Add enhanced versions of certain tools for production mode
        
        if not poc_mode:
            # Add enhanced get_models that handles large instances better
            if "get_models" not in {t["name"] for t in tools}:
                tools.append({
                    "name": "get_models",
                    "description": "Lists COMMITTED/PRODUCTION models (summarized for large instances).",
                    "inputSchema": {"type": "object", "properties": {}, "required": []}
                })
        
        logger.info(f"Total tools available: {len(tools)} (POC Mode: {poc_mode})")
        
        # Log tool breakdown for clarity
        poc_safe_count = sum(1 for t in tools if t["name"] in POC_SAFE_TOOLS)
        production_count = sum(1 for t in tools if t["name"] in PRODUCTION_ONLY_TOOLS)
        logger.info(f"  - POC-safe tools: {poc_safe_count}")
        logger.info(f"  - Production-only tools: {production_count}")
        logger.info(f"  - Other tools: {len(tools) - poc_safe_count - production_count}")
        
        return tools
    
    # ==========================================
    # TOOL EXECUTION ROUTER
    # ==========================================
    
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
        Routes to custom Python implementations or the binary.
        """
        # Sanitize looker_url
        if looker_url and not looker_url.startswith(("http://", "https://")):
             looker_url = f"https://{looker_url}"

        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        # ===========================================
        # ROUTE TO CUSTOM PYTHON IMPLEMENTATIONS
        # ===========================================
        
        # File Operations
        if tool_name == "create_project_file":
            return self._execute_create_project_file(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_project_files":
            return self._execute_get_project_files(arguments, looker_url, client_id, client_secret)
        
        # LookML Management
        elif tool_name == "dev_mode":
            return self._execute_dev_mode(arguments, looker_url, client_id, client_secret)
        elif tool_name == "validate_project":
            return self._execute_validate_project(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_git_branch_state":
            return self._execute_get_git_branch_state(arguments, looker_url, client_id, client_secret)
        
        # Context-aware Tools
        elif tool_name == "get_explore_fields_from_context":
            return self._execute_get_explore_fields_from_context(arguments, looker_url, client_id, client_secret)
        elif tool_name == "register_lookml_manually":
            return self._execute_register_lookml_manually(arguments, looker_url, client_id, client_secret)
        
        # Visualization
        elif tool_name == "create_chart_from_context":
            return self._execute_create_chart_from_context(arguments, looker_url, client_id, client_secret)
        elif tool_name == "create_dashboard":
            return self._execute_create_dashboard(arguments, looker_url, client_id, client_secret)
        elif tool_name == "add_dashboard_element":
            return self._execute_add_dashboard_element(arguments, looker_url, client_id, client_secret)
        elif tool_name == "create_dashboard_filter":
            return self._execute_create_dashboard_filter(arguments, looker_url, client_id, client_secret)
        
        # Utilities
        elif tool_name == "search_web":
            return await self._execute_search_web(arguments)
        elif tool_name == "read_url_content":
            return await self._execute_read_url_content(arguments)
        elif tool_name == "deep_search":
            return await self._execute_deep_search(arguments)
        elif tool_name == "check_internet_connection":
            return await self._execute_check_internet_connection(arguments)
        
        # GCP Data Agents (only in production mode - but keeping implementation for backwards compatibility)
        elif tool_name == "list_data_agents":
            return self._execute_list_data_agents(arguments)
        elif tool_name == "chat_with_data_agent":
            return self._execute_chat_with_data_agent(arguments)
        
        # Health Tools (only in production mode - but keeping implementation for backwards compatibility)
        elif tool_name == "health_pulse":
            return self._execute_health_pulse(looker_url, client_id, client_secret)
        elif tool_name == "health_analyze":
            return self._execute_health_analyze(looker_url, client_id, client_secret)
        elif tool_name == "health_vacuum":
            return self._execute_health_vacuum(looker_url, client_id, client_secret)
        
        # Production mode enhancements
        elif tool_name == "get_models":
            return self._execute_get_models_enhanced(looker_url, client_id, client_secret)
        elif tool_name == "get_lookml_model_explore":
            return self._execute_get_lookml_model_explore(arguments, looker_url, client_id, client_secret)
        
        # Database Metadata
        elif tool_name == "get_connections":
            return self._execute_get_connections(looker_url, client_id, client_secret)
        elif tool_name == "get_connection_schemas":
            return self._execute_get_connection_schemas(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_connection_tables":
            return self._execute_get_connection_tables(arguments, looker_url, client_id, client_secret)
        elif tool_name == "get_connection_columns":
            return self._execute_get_connection_columns(arguments, looker_url, client_id, client_secret)
        
        # New Python implementation for query_url ensuring full URLs
        elif tool_name == "query_url":
            return self._execute_query_url(arguments, looker_url, client_id, client_secret)
        
        # ===========================================
        # ROUTE TO BINARY (fallback for all other tools)
        # ===========================================
        
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
    
    # ==========================================
    # CUSTOM TOOL IMPLEMENTATIONS
    # ==========================================
    
    def _execute_create_project_file(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create file using deploy script for robustness. AUTO-REGISTERS to context."""
        try:
            project_id = args.get("project_id")
            path = args.get("path")
            source = args.get("source", "")
            
            # Write source to temp file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".lkml") as tmp:
                tmp.write(source)
                tmp_path = tmp.name
            
            # Validate Context for Models
            if path.endswith('.model.lkml') and "connection:" not in source:
                 return {
                     "success": False, 
                     "error": "Missing Connection Name. Please ask the user which database connection to use."
                 }
                 
            # Resolve deploy_lookml.py path correctly (moved to scripts/)
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            deploy_script = os.path.join(root_dir, "scripts", "deploy_lookml.py")
            
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
            env["LOOKERSDK_VERIFY_SSL"] = "false"  # POC mode
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            os.unlink(tmp_path)
            
            if result.returncode == 0:
                # AUTO-REGISTRATION
                registered = []
                try:
                    if self.lookml_context and LookMLParser:
                        if path.endswith('.view.lkml'):
                            view_meta = LookMLParser.parse_view(source)
                            if view_meta:
                                self.lookml_context.register_view(
                                    view_meta.name, 
                                    view_meta.fields, 
                                    view_meta.sql_table_name
                                )
                                registered.append(f"View: {view_meta.name}")
                                
                        elif path.endswith('.model.lkml'):
                            model_name = os.path.basename(path).replace('.model.lkml', '')
                            model_meta = LookMLParser.parse_model(source, model_name)
                            if model_meta:
                                self.lookml_context.register_model(
                                    model_meta.name, 
                                    model_meta.connection, 
                                    model_meta.explores, 
                                    model_meta.includes
                                )
                                registered.append(f"Model: {model_meta.name}")
                                
                                # Auto-register explores found in the model file
                                explores_raw = re.split(r'explore:\s+', source)[1:]
                                for raw in explores_raw:
                                    explore_block = f"explore: {raw}"
                                    explore_meta = LookMLParser.parse_explore(explore_block)
                                    
                                    if explore_meta:
                                        self.lookml_context.register_explore(
                                            model=model_name,
                                            explore=explore_meta.explore_name,
                                            base_view=explore_meta.base_view,
                                            joins=explore_meta.joins
                                        )
                                        registered.append(f"Explore: {explore_meta.explore_name}")

                    return {
                        "success": True, 
                        "result": f"Created {path}",
                        "auto_registered": registered
                    }
                except Exception as parse_e:
                    logger.warning(f"Auto-registration failed: {parse_e}")
                    return {"success": True, "result": f"Created {path} (Auto-registration warning: {parse_e})"}
                    
            else:
                logger.error(f"Deploy failed. Stdout: {result.stdout}, Stderr: {result.stderr}")
                return {"success": False, "error": f"Deploy script failed: {result.stderr or result.stdout}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_project_files(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List files in project OR read a specific file if file_id provided."""
        try:
            project_id = args.get("project_id")
            file_id = args.get("file_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # If file_id provided, read that specific file
            if file_id:
                file = sdk.project_file(project_id, file_id)
                return {"success": True, "result": {"path": file_id, "content": file.content}}
            
            # Otherwise, list all files
            files = sdk.all_project_files(project_id)
            return {
                "success": True, 
                "result": [{"id": f.id, "path": f.path, "type": f.type} for f in files]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_dev_mode(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Enter or exit dev mode."""
        try:
            from looker_sdk import models40
            enable = args.get("enable", True)
            sdk = self._init_sdk(url, client_id, client_secret)
            session = sdk.update_session(models40.WriteApiSession(workspace_id="dev" if enable else "production"))
            return {"success": True, "result": f"Workspace set to: {session.workspace_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

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

    def _execute_query_url(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Generate an explore URL for a query.
        Replaces binary implementation to ensure we return a FULL URL (not /x/ short link)
        that can be correctly embedded by the frontend.
        """
        try:
            from looker_sdk import models40
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # Map arguments to WriteQuery
            model = args.get("model")
            view = args.get("view") or args.get("explore") # 'explore' is commonly used key
            fields = args.get("fields", [])
            filters = args.get("filters", {})
            sorts = args.get("sorts", [])
            limit = args.get("limit", "500")
            
            if not model or not view:
                return {"success": False, "error": "Missing model or view/explore"}

            query_body = models40.WriteQuery(
                model=model,
                view=view,
                fields=fields,
                filters=filters,
                sorts=sorts,
                limit=limit
            )
            
            query = sdk.create_query(body=query_body)
            
            # Construct the FULL URL manually to ensure it works for embedding
            # Format: <base_url>/explore/<model>/<view>?qid=<client_id>
            
            # Ensure base URL has protocol
            base_url = url.rstrip('/')
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"
                
            # Add &toggle=dat,pik,vis to ensure Data, Picker, and Visualization are visible
            long_url = f"{base_url}/explore/{model}/{view}?qid={query.client_id}&toggle=dat,pik,vis"
            
            return {
                "success": True,
                "result": f"The query URL is: {long_url}"
            }
            
        except Exception as e:
            logger.error(f"query_url failed: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_git_branch_state(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Get git branch state."""
        try:
            project_id = args.get("project_id")
            sdk = self._init_sdk(url, client_id, client_secret)
            branch = sdk.git_branch(project_id)
            return {"success": True, "result": str(branch)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === PRODUCTION-ONLY TOOLS (kept for backwards compatibility) ===
    # These are not available in POC mode but kept to avoid breaking existing code
    
    def _execute_get_projects(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List projects (production only)."""
        try:
            sdk = self._init_sdk(url, client_id, client_secret)
            projects = sdk.all_projects()
            return {"success": True, "result": [{"id": p.id, "name": p.name} for p in projects]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_project(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create project (production only)."""
        try:
            from looker_sdk import models40
            name = args.get("name")
            sdk = self._init_sdk(url, client_id, client_secret)
            project = sdk.create_project(models40.WriteProject(name=name))
            return {"success": True, "result": f"Created project {project.id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_explore_fields_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Fetch available fields for an uncommitted explore from the session context."""
        if not getattr(self, 'poc_mode', False):
             return {"success": False, "error": "❌ This tool is only available in POC Mode."}

        try:
            if not self.lookml_context:
                return {"success": False, "error": "LookMLContext not available"}
                
            model_name = args.get("model_name")
            explore_name = args.get("explore_name")
            
            if not self.lookml_context.has_explore(model_name, explore_name):
                 return {
                     "success": False, 
                     "error": f"Explore {model_name}.{explore_name} not found in session context. Did you create it in this session?"
                 }

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

    def _execute_register_lookml_manually(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Manually register LookML artifacts to the context."""
        if not getattr(self, 'poc_mode', False):
             return {"success": False, "error": "❌ This tool is only available in POC Mode."}

        try:
            if not self.lookml_context or not Field:
                return {"success": False, "error": "LookMLContext not available"}

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

    def _execute_create_chart_from_context(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create a single chart using uncommitted LookML."""
        if not getattr(self, 'poc_mode', False):
             return {"success": False, "error": "❌ This tool is only available in POC Mode."}

        try:
            from looker_sdk import models40
            sdk = self._init_sdk(url, client_id, client_secret)
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            model = args.get("model_name")
            explore = args.get("explore_name")
            
            # Construct Query
            query_body = models40.WriteQuery(
                model=model,
                view=explore,
                fields=args.get("fields", []),
                filters=args.get("filters"),
                sorts=args.get("sorts"),
                limit=args.get("limit", "500"),
                vis_config={"type": args.get("vis_type", "looker_grid")}
            )
            
            # Create Query & Get Slug
            created_query = sdk.create_query(body=query_body)
            query_slug = created_query.client_id
            
            # Construct Explore Embed URL
            base_url = url.rstrip("/")
            explore_url = f"{base_url}/embed/explore/{model}/{explore}?qid={query_slug}&toggle=dat,pik,vis"
            
            logger.info(f"✅ Created chart: {explore_url}")
            
            # Run Inline for Data Summary
            json_results = sdk.run_inline_query(
                result_format="json",
                body=query_body
            )
            data_summary = json_results[:5] if json_results else []
            
            return {
                "success": True,
                "result": {
                    "url": explore_url,
                    "data_preview": data_summary,
                    "message": f"Chart created for {model}.{explore}"
                }
            }
        except Exception as e:
            logger.error(f"Failed to create chart: {e}")
            return {"success": False, "error": str(e)}

    # REMOVED: create_dashboard_from_context (redundant with create_dashboard + add_dashboard_element)
    # If needed, use the pattern: create_dashboard() -> multiple add_dashboard_element() calls
    # This is cleaner and gives better control over individual tiles

    def _execute_create_dashboard(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        STEP 1: Creates a new empty User Defined Dashboard (UDD).
        Returns dashboard_id and base_url for subsequent add_dashboard_element calls.
        """
        try:
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            title = args.get("title", "Untitled Dashboard")
            
            # Find Personal Folder
            folder_id = None
            try:
                me = sdk.me()
                if me.personal_folder_id:
                    folder_id = me.personal_folder_id
                else:
                    personal = next((f for f in sdk.all_folders() if f.is_personal), None)
                    if personal:
                        folder_id = personal.id
            except Exception as e:
                logger.warning(f"Could not find personal folder: {e}")

            # Create dashboard
            dashboard = sdk.create_dashboard(models40.WriteDashboard(
                title=title,
                folder_id=folder_id 
            ))
            
            # Extract base URL
            base_url = url.rstrip("/")
            full_url = f"{base_url}/embed/dashboards/{dashboard.id}"
            
            logger.info(f"✅ Created dashboard: ID={dashboard.id}, URL={full_url}")
            
            # RETURN LOCKED URL TO PREVENT HALLUCINATION
            return {
                "success": True,
                "result": {
                    "dashboard_id": dashboard.id,
                    "title": dashboard.title,
                    "base_url": base_url,
                    "full_url": full_url,
                    "message": f"Dashboard created. ID: {dashboard.id}. Proceed to add tiles."
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create dashboard: {str(e)}"}

    def _execute_add_dashboard_element(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        STEP 2: Adds a tile to a UDD.
        REQUIRES dashboard_id from create_dashboard output.
        """
        try:
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
            dashboard_id = args.get("dashboard_id")
            title = args.get("title")
            vis_type = args.get("type", "looker_grid")
            query_id = args.get("query_id")
            query_def = args.get("query_def")
            
            if not dashboard_id:
                return {"success": False, "error": "dashboard_id is required (from create_dashboard output)"}
            
            if not query_id and not query_def:
                return {"success": False, "error": "Must provide either query_id or query_def"}
            
            if not query_id and query_def:
                # Create the query from definition
                query_body = models40.WriteQuery(
                    model=query_def.get("model"),
                    view=query_def.get("explore"),
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
            
            return {
                "success": True, 
                "result": f"Added tile '{title}' (element_id={created_elem.id}) to dashboard {dashboard_id}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_create_dashboard_filter(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Add a filter to an existing dashboard."""
        try:
            from looker_sdk import models40
            
            sdk = self._init_sdk(url, client_id, client_secret)
            sdk.update_session(models40.WriteApiSession(workspace_id="dev"))
            
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

    def _search_web_manual_fallback(self, query: str) -> List[Dict[str, str]]:
        """Fallback search using manual requests to DuckDuckGo HTML endpoint."""
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            
            logger.info(f"Attempting manual search fallback for: {query}")
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Manual fallback status code: {resp.status_code}")
                return []

            # Regex to find results (title and link)
            content = resp.text
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, content)
            
            results = []
            for url, title_html in matches:
                title = html.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
                # Basic result structure matching DDGS
                results.append({"title": title, "href": url, "body": title}) # Body is same as title in this simple fallback
            
            return results[:5]
        except Exception as e:
            logger.error(f"Manual fallback failed: {e}")
            return []

    async def _search_web_manual_fallback(self, query: str) -> List[Dict[str, str]]:
        """Fallback search using manual requests to DuckDuckGo HTML endpoint."""
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            
            logger.info(f"Attempting manual search fallback for: {query}")
            
            # Run blocking request in thread
            def do_request():
                return requests.post(url, data=data, headers=headers, timeout=10)

            resp = await asyncio.to_thread(do_request)
            
            if resp.status_code != 200:
                logger.warning(f"Manual fallback status code: {resp.status_code}")
                return []

            # Regex to find results (title and link)
            content = resp.text
            # Basic pattern for DDG HTML results
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, content)
            
            results = []
            for url, title_html in matches:
                title = html.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
                # Basic result structure matching DDGS
                results.append({"title": title, "href": url, "body": title}) # Body is same as title in this simple fallback
            
            return results[:5]
        except Exception as e:
            logger.error(f"Manual fallback failed: {e}")
            return []

    async def _execute_search_web(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web with timeout and error handling."""
        try:
            query = args.get("query")
            if not query:
                return {
                    "error": True,
                    "error_type": "INVALID_INPUT",
                    "message": "No query provided"
                }
            
            # Helper for searching to run in thread
            def do_search():
                last_error = None
                # Attempt 1: Specific region and safesearch off
                try:
                    gen = DDGS().text(query, max_results=8, region="wt-wt", safesearch="off")
                    results = list(gen) if gen else []
                    if results: return results, None
                except Exception as e:
                    last_error = e
                    logger.warning(f"DDGS Attempt 1 failed: {e}")

                # Attempt 2: Broad search (no region)
                try:
                    logger.info("Retrying search without region...")
                    gen = DDGS().text(query, max_results=8)
                    results = list(gen) if gen else []
                    if results: return results, None
                except Exception as e:
                    last_error = e
                    logger.warning(f"DDGS Attempt 2 failed: {e}")
                
                # Attempt 3: Try splitting query if long (simple heuristic)
                if len(query.split()) > 5:
                     simple_query = " ".join(query.split()[:5])
                     try:
                        logger.info(f"Retrying with simplified query: {simple_query}")
                        gen = DDGS().text(simple_query, max_results=5)
                        results = list(gen) if gen else []
                        if results: return results, None
                     except Exception as e:
                        last_error = e
                        logger.warning(f"DDGS Attempt 3 failed: {e}")
                
                return [], last_error

            # Run with timeout
            try:
                # 10 second timeout
                results, error = await asyncio.wait_for(asyncio.to_thread(do_search), timeout=10.0)
            except asyncio.TimeoutError:
                # TIMEOUT: Try manual fallback
                logger.warning("DDGS timed out, attempting manual fallback...")
                results = await self._search_web_manual_fallback(query)
                if results:
                     return {
                        "success": True,
                        "result": results
                    }
                
                return {
                    "error": True,
                    "error_type": "TIMEOUT",
                    "message": "Web search timed out (10s limit)",
                    "details": "The search service did not respond in time."
                }
            except Exception as e:
                # ERROR: Try manual fallback
                logger.warning(f"DDGS failed ({e}), attempting manual fallback...")
                results = await self._search_web_manual_fallback(query)
                if results:
                    return {
                        "success": True,
                        "result": results
                    }

                return {
                    "error": True,
                    "error_type": "SEARCH_FAILED",
                    "message": f"Web search unavailable: {str(e)}",
                    "details": str(e)
                }

            if not results:
                # NO RESULTS: Try manual fallback if error present or strict failure
                if error:
                    logger.warning(f"DDGS returned no results with error ({error}), attempting manual fallback...")
                    results = await self._search_web_manual_fallback(query)
                    if results:
                        return {
                            "success": True,
                            "result": results
                        }
                    
                    return {
                        "error": True, 
                        "error_type": "SEARCH_FAILED", 
                        "message": f"Web search unavailable: {error}",
                        "details": str(error)
                    }
                
                # Double check manual fallback even for "no results" just in case DDGS is being weird
                logger.info("DDGS returned no results (safe), attempting manual fallback to be sure...")
                results = await self._search_web_manual_fallback(query)
                if results:
                     return {
                        "success": True,
                        "result": results
                    }

                return {
                    "error": True,
                    "error_type": "NO_RESULTS",
                    "message": "The web search returned no results. Try a broader query."
                }
                return {
                    "error": True,
                    "error_type": "NO_RESULTS",
                    "message": "The web search returned no results. Try a broader query."
                }

            return {
                "success": True,
                "result": results
            }
        except Exception as e:
            logger.error(f"Search wrapper failed: {e}")
            return {
                "error": True,
                "error_type": "SYSTEM_ERROR",
                "message": f"Web search system error: {str(e)}",
                "details": str(e)
            }

    async def _execute_check_internet_connection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check external internet connectivity."""
        try:
            logger.info("Checking internet connection...")
            def do_check():
                try:
                    requests.get("https://www.google.com", timeout=5)
                    return True, "Connected to Google"
                except:
                    try:
                        requests.get("https://1.1.1.1", timeout=5)
                        return True, "Connected to Cloudflare DNS"
                    except Exception as e:
                        return False, str(e)

            success, msg = await asyncio.to_thread(do_check)
            if success:
                return {"success": True, "message": "Internet connection active", "details": msg}
            else:
                return {
                    "error": True, 
                    "error_code": "NO_CONNECTION", 
                    "message": "No internet connection", 
                    "details": msg
                }
        except Exception as e:
             return {"error": True, "message": str(e)}

    async def _execute_check_internet_connection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check external internet connectivity."""
        try:
            logger.info("Checking internet connection...")
            def do_check():
                try:
                    requests.get("https://www.google.com", timeout=5)
                    return True, "Connected to Google"
                except:
                    try:
                        requests.get("https://1.1.1.1", timeout=5)
                        return True, "Connected to Cloudflare DNS"
                    except Exception as e:
                        return False, str(e)

            success, msg = await asyncio.to_thread(do_check)
            if success:
                return {"success": True, "message": "Internet connection active", "details": msg}
            else:
                return {
                    "error": True, 
                    "error_code": "NO_CONNECTION", 
                    "message": "No internet connection", 
                    "details": msg
                }
        except Exception as e:
             return {"error": True, "message": str(e)}


    async def _execute_read_url_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a URL with robust error handling."""
        url = args.get("url")
        if not url:
            return {"error": True, "message": "No URL provided", "error_code": "INVALID_INPUT"}
            
        logger.info(f"Reading content from: {url}")
        
        def do_read():
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            try:
                # 15s timeout
                resp = requests.get(url, headers=headers, timeout=15)
                
                if resp.status_code != 200:
                    raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}")
                
                # Simple HTML to Text conversion
                from html.parser import HTMLParser
                
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                        self.ignore = False
                        
                    def handle_starttag(self, tag, attrs):
                        if tag in ['script', 'style', 'head', 'title', 'meta', 'link']:
                            self.ignore = True
                            
                    def handle_endtag(self, tag):
                        if tag in ['script', 'style', 'head', 'title', 'meta', 'link']:
                            self.ignore = False
                            
                    def handle_data(self, data):
                        if not self.ignore and data.strip():
                            self.text_parts.append(data.strip())
                            
                    def get_text(self):
                        return " ".join(self.text_parts)

                parser = TextExtractor()
                parser.feed(resp.text)
                text = parser.get_text()
                
                # Limit content
                return text[:8000] + "..." if len(text) > 8000 else text

            except requests.exceptions.Timeout:
                raise TimeoutError("Connection timed out")
            except requests.exceptions.ConnectionError:
                raise ConnectionError("Failed to connect to server")
            except Exception as e:
                raise e

        try:
            content = await asyncio.to_thread(do_read)
            return {
                "success": True,
                "url": url,
                "content": content
            }
        except TimeoutError:
            return {
                "error": True,
                "error_code": "TIMEOUT",
                "message": "Request timed out (15s)",
                "details": "Server took too long to respond. Try a different source."
            }
        except ConnectionError:
            return {
                "error": True,
                "error_code": "CONNECTION_ERROR",
                "message": "Failed to connect to server",
                "details": "Check domain name or usage of VPN/Proxy."
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": True,
                "error_code": "HTTP_ERROR",
                "message": str(e),
                "details": "Server returned an error code."
            }
        except Exception as e:
            logger.error(f"Read URL failed: {e}")
            return {
                "error": True,
                "error_code": "SYSTEM_ERROR",
                "message": f"Failed to read URL: {str(e)}",
                "details": str(e)
            }

    async def _execute_deep_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a search and read the content of top results."""
        try:
            query = args.get("query")
            max_results = min(args.get("max_results", 3), 5) # Cap at 5
            
            # Step 1: Search
            search_args = {"query": query}
            search_result = await self._execute_search_web(search_args)
            
            if search_result.get("error"):
                return search_result
            
            results = search_result.get("result", [])
            if not results:
                return {
                    "error": True,
                    "error_code": "NO_RESULTS",
                    "message": "Search returned no results",
                    "details": "Try a broader query or checked internet connection."
                }

            top_results = results[:max_results]
            
            # Step 2: Read content for each result
            rich_results = []
            for item in top_results:
                url = item.get("href")
                if url:
                    content_res = await self._execute_read_url_content({"url": url})
                    if content_res.get("success"):
                         item["content"] = content_res.get("content")
                    else:
                         # Preserve error info
                         item["content_error"] = content_res.get("message")
                         item["content_error_code"] = content_res.get("error_code")
                         item["content"] = f"[Failed to read: {content_res.get('message')}]"
                    
                    rich_results.append(item)
            
            return {
                "success": True,
                "query": query,
                "results": rich_results
            }
            
        except Exception as e:
            logger.error(f"Deep search failed: {e}")
            return {
                "error": True, 
                "message": f"Deep search failed: {str(e)}"
            }

    # === GCP DATA AGENTS (Production only - kept for backwards compatibility) ===
    def _get_gcp_token(self):
        """Get GCP auth token."""
        credentials, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token

    def _execute_list_data_agents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List GCP Data Agents."""
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
        """Chat with GCP Data Agent."""
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

    def _execute_health_pulse(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Check Looker health."""
        try:
            sdk = self._init_sdk(url, client_id, client_secret)
            user = sdk.me()
            return {
                "success": True,
                "result": f"Looker is healthy. Connected as: {user.display_name} ({user.email})",
                "user": {"id": user.id, "email": user.email}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_health_analyze(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Analyze content validation problems."""
        try:
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
            sdk = self._init_sdk(url, client_id, client_secret)
            deleted = sdk.search_dashboards(deleted=True, limit=10)
            return {
                "success": True,
                "result": f"Found {len(deleted)} deleted dashboards that can be permanently removed."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_models_enhanced(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Get all models with detailed information using all_lookml_models.
        """
        try:
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # Use all_lookml_models as requested/verified
            # Specifying subfields is safer: explores(name)
            models = sdk.all_lookml_models(fields="name,project_name,explores(name)")
            
            model_list = []
            for model in models:
                explores = [explore.name for explore in (model.explores or [])]
                model_list.append({
                    "name": model.name,
                    "project_name": model.project_name,
                    "explores": explores,
                    "explore_count": len(explores)
                })
            
            return {
                "success": True,
                "result": {
                    "models": model_list,
                    "count": len(model_list),
                    "message": f"Found {len(model_list)} models in project"
                }
            }
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {"success": False, "error": str(e)}

    def _execute_get_lookml_model_explore(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Get explore metadata."""
        try:
            model = args.get("model_name")
            explore = args.get("explore_name")
            sdk = self._init_sdk(url, client_id, client_secret)
            exp = sdk.lookml_model_explore(model, explore)
            return {
                "success": True, 
                "result": f"Explore {model}.{explore} exists with {len(exp.fields.dimensions)} dims"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_get_connections(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List connections."""
        try:
            sdk = self._init_sdk(url, client_id, client_secret)
            connections = sdk.all_connections()
            return {
                "success": True, 
                "result": [
                    {
                        "name": conn.name,
                        "dialect": conn.dialect.name if conn.dialect else "unknown",
                        "host": conn.host,
                        "database": conn.database
                    } 
                    for conn in connections
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    def _execute_get_connection_schemas(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List schemas for a connection."""
        try:
            connection_name = args.get("connection_name")
            if not connection_name:
                return {"success": False, "error": "connection_name is required"}
            
            sdk = self._init_sdk(url, client_id, client_secret)
            schemas = sdk.connection_schemas(connection_name)
            return {
                "success": True,
                "result": [schema.name for schema in schemas if schema.name]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    def _execute_get_connection_tables(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List tables in a schema with robust error handling and BigQuery support."""
        try:
            connection_name = args.get("connection_name")
            schema_name = args.get("schema_name")
            
            if not connection_name:
                return {"success": False, "error": "connection_name is required"}
            
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # Get connection info to determine dialect
            try:
                connection = sdk.connection(connection_name)
                dialect = connection.dialect.name if connection.dialect else "unknown"
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Connection '{connection_name}' not found. Use get_connections to see available connections. Error: {str(e)}"
                }
            
            # Get all schema/table combinations
            try:
                schema_tables_list = sdk.connection_tables(connection_name, schema_name=schema_name if schema_name else None)
                
                # schema_tables_list is a list of SchemaTables objects
                # Each has: name (schema name) and tables (list of table names)
                
                if not schema_name:
                    # Return all tables from all schemas
                    all_tables = []
                    for schema_obj in schema_tables_list:
                        schema = schema_obj.name
                        tables = schema_obj.tables or []
                        for table_obj in tables:
                            # Extract table name from SchemaTable object
                            table_name = table_obj.name if hasattr(table_obj, 'name') else str(table_obj)
                            all_tables.append({
                                "name": table_name,
                                "schema": schema
                            })
                    
                    return {
                        "success": True,
                        "result": all_tables,
                        "message": f"Retrieved {len(all_tables)} tables from {len(schema_tables_list)} schemas. Specify schema_name to filter."
                    }
                else:
                    # Filter to specific schema
                    matching_schema = None
                    for schema_obj in schema_tables_list:
                        if schema_obj.name == schema_name:
                            matching_schema = schema_obj
                            break
                    
                    if matching_schema and matching_schema.tables:
                        # Extract table names from SchemaTable objects
                        table_names = [
                            table_obj.name if hasattr(table_obj, 'name') else str(table_obj)
                            for table_obj in matching_schema.tables
                        ]
                        return {
                            "success": True,
                            "result": table_names,
                            "message": f"Found {len(table_names)} tables in schema '{schema_name}'"
                        }
                    elif matching_schema:
                        return {
                            "success": True,
                            "result": [],
                            "message": f"Schema '{schema_name}' exists but contains no tables"
                        }
                    else:
                        # Schema not found - list available schemas
                        available_schemas = [s.name for s in schema_tables_list if s.name]
                        return {
                            "success": False,
                            "error": f"Schema '{schema_name}' not found. Available schemas: {', '.join(available_schemas[:10])}"
                        }
                        
            except Exception as e:
                return {"success": False, "error": f"Failed to retrieve tables: {str(e)}"}
            
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
        
    def _execute_get_connection_columns(self, args: Dict[str, Any], url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """List columns in a table with robust error handling and BigQuery support."""
        try:
            connection_name = args.get("connection_name")
            schema_name = args.get("schema_name")
            table_name = args.get("table_name")
            
            if not connection_name:
                return {"success": False, "error": "connection_name is required"}
            if not table_name:
                return {"success": False, "error": "table_name is required"}
            
            sdk = self._init_sdk(url, client_id, client_secret)
            
            # Get connection info to determine dialect
            try:
                connection = sdk.connection(connection_name)
                dialect = connection.dialect.name if connection.dialect else "unknown"
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Connection '{connection_name}' not found. Error: {str(e)}"
                }
            
            # If no schema provided, try to find the table
            if not schema_name:
                try:
                    # Get all tables to find which schema contains this table
                    all_tables = sdk.connection_tables(connection_name)
                    matching_tables = [t for t in all_tables if t.name == table_name]
                    
                    if not matching_tables:
                        return {
                            "success": False,
                            "error": f"Table '{table_name}' not found in any schema. Specify schema_name parameter."
                        }
                    elif len(matching_tables) > 1:
                        schemas = [t.schema_name for t in matching_tables]
                        return {
                            "success": False,
                            "error": f"Table '{table_name}' exists in multiple schemas: {schemas}. Specify schema_name parameter."
                        }
                    else:
                        schema_name = matching_tables[0].schema_name
                        logger.info(f"Auto-detected schema '{schema_name}' for table '{table_name}'")
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to auto-detect schema: {str(e)}. Please specify schema_name parameter."
                    }
            
            # Try different parameter combinations
            errors = []
            
            # Attempt 1: Standard schema_name + table_names (note: plural)
            try:
                columns = sdk.connection_columns(
                    connection_name,
                    schema_name=schema_name,
                    table_names=table_name  # API uses table_names (plural)
                )
                if columns:
                    # connection_columns returns a list of SchemaColumns objects
                    # Each SchemaColumns has a 'name' (schema) and 'columns' (list of column objects)
                    all_columns = []
                    for schema_cols in columns:
                        if schema_cols.columns:
                            for col in schema_cols.columns:
                                all_columns.append({
                                    "name": col.name,
                                    "type": col.data_type_looker if hasattr(col, 'data_type_looker') else col.data_type,
                                    "sql_type": col.data_type_database if hasattr(col, 'data_type_database') else col.data_type
                                })
                    
                    if all_columns:
                        return {
                            "success": True,
                            "result": all_columns,
                            "message": f"Retrieved {len(all_columns)} columns from {schema_name}.{table_name}"
                        }
            except Exception as e:
                errors.append(f"schema_name parameter: {str(e)}")
            
            # Attempt 2: database + table_names (BigQuery)
            if "bigquery" in dialect.lower():
                try:
                    columns = sdk.connection_columns(
                        connection_name,
                        database=schema_name,
                        table_names=table_name
                    )
                    if columns:
                        all_columns = []
                        for schema_cols in columns:
                            if schema_cols.columns:
                                for col in schema_cols.columns:
                                    all_columns.append({
                                        "name": col.name,
                                        "type": col.data_type_looker if hasattr(col, 'data_type_looker') else col.data_type,
                                        "sql_type": col.data_type_database if hasattr(col, 'data_type_database') else col.data_type
                                    })
                        
                        if all_columns:
                            return {
                                "success": True,
                                "result": all_columns,
                                "message": f"Retrieved {len(all_columns)} columns using database parameter"
                            }
                except Exception as e:
                    errors.append(f"database parameter: {str(e)}")
            
            # Attempt 3: With cache=False
            try:
                columns = sdk.connection_columns(
                    connection_name,
                    schema_name=schema_name,
                    table_names=table_name,
                    cache=False  # Force fresh data
                )
                if columns:
                    all_columns = []
                    for schema_cols in columns:
                        if schema_cols.columns:
                            for col in schema_cols.columns:
                                all_columns.append({
                                    "name": col.name,
                                    "type": col.data_type_looker if hasattr(col, 'data_type_looker') else col.data_type,
                                    "sql_type": col.data_type_database if hasattr(col, 'data_type_database') else col.data_type
                                })
                    
                    if all_columns:
                        return {
                            "success": True,
                            "result": all_columns,
                            "message": f"Retrieved {len(all_columns)} columns (cache disabled)"
                        }
            except Exception as e:
                errors.append(f"cache=False: {str(e)}")
            
            # All attempts failed
            return {
                "success": False,
                "error": f"Failed to retrieve columns for {schema_name}.{table_name}. Verify table exists using get_connection_tables. Attempts: {'; '.join(errors)}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    # ==========================================
    # SYSTEM PROMPT BUILDER
    # ==========================================
    
    def _build_system_prompt(
        self, 
        gcp_project: str, 
        gcp_location: str, 
        looker_url: str = "", 
        explore_context: str = "", 
        poc_mode: bool = False
    ) -> str:
        """
        Constructs the system prompt for the agent with clear POC mode restrictions.
        """
        system_prompt = (
            f"You are a Looker assistant with direct access to Looker MCP tools.\n"
            f"Active GCP Project: {gcp_project}, Location: {gcp_location}\n\n"
        )

        # TOOL INTEGRITY RULES (applies to ALL modes)
        system_prompt += (
            "🛡️ TOOL INTEGRITY RULES (MANDATORY - READ BEFORE ANY TOOL CALL)\n\n"

            "RULE 1 - CONTEXT EXISTENCE CHECK (_from_context tools):\n"
            "BEFORE using ANY '_from_context' tool (get_explore_fields_from_context, "
            "create_query_from_context, create_chart_from_context), verify:\n"
            "  ✅ USE _from_context IF: You created LookML files THIS session, OR previously "
            "queried this model/explore THIS session, OR called register_lookml_manually.\n"
            "  ❌ DO NOT USE _from_context IF: This is the first mention of the model/explore, "
            "OR the user referenced it but you haven't accessed it yet.\n"
            "  → Instead use: get_models → get_explore_fields (production) or get_project_files → "
            "register_lookml_manually → then _from_context.\n\n"

            "RULE 2 - NAMING DISAMBIGUATION (CRITICAL):\n"
            "  A. PROJECT vs MODEL:\n"
            "     PROJECT = Repository name (e.g. 'my_project')\n"
            "     MODEL = .model.lkml file (e.g. 'marketing')\n"
            "     NEVER substitute model name as project_id.\n\n"
            "  B. EXPLORE vs BASE VIEW (THE #1 CAUSE OF BROKEN TILES):\n"
            "     EXPLORE NAME = The name defined in `explore: name {}`.\n"
            "     BASE VIEW = The `from` parameter (or explore name if missing).\n"
            "     ❌ INCORRECT: `explore: orders { from: order_items }` -> Using 'order_items' as explore name.\n"
            "     ✅ CORRECT: Use 'orders' (the EXPLORE NAME) in all API calls and URLs.\n"
            "     WHEN DEFINING QUERY: `model='model_name', view='EXPLORE_NAME'` (NOT base view!)\n"
            "     ALWAYS check the `explore:` definition line, NOT the `from:` line.\n\n"

            "RULE 3 - MANDATORY RESPONSE REPORTING:\n"
            "  After EVERY tool call, you MUST state the outcome before deciding next steps:\n"
            "    ✅ Success with data: '✅ get_models returned 47 models'\n"
            "    ⚠️ Success but empty: '⚠️ get_models returned no data (could be API issue, "
            "permissions, or no models deployed)'\n"
            "    ❌ Error: '❌ get_project_files failed: 404 - project X not found'\n"
            "  ❌ FORBIDDEN: Silent tool calls, jumping to workarounds without explaining why "
            "the primary path failed, or saying 'I see the issue...' without showing what you saw.\n\n"
        )
        
        # AUTOMATIC QUERY VISUALIZATION PROTOCOL (MANDATORY)
        system_prompt += (
            "📊 **AUTOMATIC QUERY VISUALIZATION PROTOCOL** (MANDATORY)\n"
            "For ALL data analysis requests resulting in a single query/chart:\n"
            "1. **Run Query:** Use `query` or `run_look` to get data.\n"
            "2. **Get Embed URL:** IMMEDIATELY call `query_url` with IDENTICAL parameters.\n"
            "3. **Extract URL:** Use the EXACT `result` from `query_url` response.\n"
            "   ✅ DO: Use the exact string provided (it contains /explore/...)\n"
            "   ❌ DON'T: Construct URLs, assume domains, or modify the returned URL.\n"
            "4. **Present Link:** Format as Markdown: `[Interactive Chart]({exact_url_from_response})`\n"
            "5. **Provide Insights:** Analyze the data returned in Step 1.\n\n"
        )
        
        # MANDATORY DASHBOARD CREATION SEQUENCE
        system_prompt += (
            "🏗️ **MANDATORY DASHBOARD CREATION SEQUENCE** (PREVENTS HALLUCINATIONS)\n"
            "When creating a dashboard, you MUST follow this strict sequence:\n"
            "STEP 1: <invoke name='create_dashboard'> [STOP - WAIT FOR RESPONSE]\n"
            "STEP 2: EXTRACT these values from the response:\n"
            "   - `dashboard_id`: Use in ALL `add_dashboard_element` calls\n"
            "   - `full_url`: The COMPLETE embed URL to present to user\n"
            "STEP 3: Loop for EACH tile:\n"
            "   - <invoke name='add_dashboard_element'> with `dashboard_id=X`, `query_def` or `query_id`.\n"
            "   - [STOP - WAIT FOR RESPONSE] - verify success.\n"
            "STEP 4: <invoke name='create_dashboard_filter'> with `dashboard_id=X`. (MANDATORY: At least 1 filter).\n"
            "STEP 5: ONLY AFTER ALL TILES ADDED: Present link using the `full_url` from Step 2.\n"
            "   ✅ CORRECT: `[Interactive Dashboard](https://your-instance.com/embed/dashboards/123)` (from tool output)\n"
            "   ❌ INCORRECT: `[Interactive Dashboard](https://googledemo.looker.com/...)` (Hallucinated domain)\n"
            "❌ **STRICTLY FORBIDDEN:**\n"
            "   - Claiming 'Tile added' without an actual successful tool call.\n"
            "   - Generating text like '✅ Tile 1 added... ✅ Tile 2 added...' in a single turn without intermediate tool calls.\n"
            "   - Embedding the dashboard link before tiles are added.\n"
            "   - ⛔ **Creating a dashboard for a single visualization.** Use `query_url` (or `create_chart_from_context` in POC) instead.\n\n"
        )
        
        # URL INTEGRITY RULES
        system_prompt += (
            "🔒 **URL INTEGRITY RULES** (ZERO TOLERANCE)\n"
            "⛔ NEVER invent domain names (googledemo, looker-demo, etc.)\n"
            "⛔ NEVER construct URLs from memory or patterns\n"
            "⛔ NEVER use Looker Short Links (`/x/...`) - they break authentication.\n"
            "✅ ALWAYS extract from tool response fields (especially `query_url` result).\n"
            "✅ ALWAYS verify you have the actual URL before presenting.\n\n"
        )

        # POC MODE vs PRODUCTION MODE
        if poc_mode:
            system_prompt += (
                "🚨 **POC MODE ACTIVE** 🚨\n"
                "You are STRICTLY RESTRICTED to uncommitted/context tools only.\n\n"
                
                "❌ **FORBIDDEN TOOLS** (DO NOT USE UNDER ANY CIRCUMSTANCES):\n"
                "   - `run_query` (requires committed LookML)\n"
                "   - `get_models` (shows only committed models)\n"
                "   - `get_explores` (shows only committed explores)\n"
                "   - `get_lookml_model_explore` (requires committed LookML)\n"
                "   - `query_url` (requires committed LookML)\n"
                "   - `create_chart` (production version - requires committed LookML)\n"
                "   - Any other tool that requires committed/production LookML\n\n"
                
                "✅ **ALLOWED TOOLS** (work with uncommitted LookML):\n"
                "   File Operations:\n"
                "   - `create_project_file` (creates new LookML files)\n"
                "   - `get_project_files`, `get_project_file`\n"
                "   - `validate_project`, `dev_mode`\n\n"
                "   🚨 **POC MANDATE**: When creating a MODEL file, you MUST ALWAYS include: `include: \"/*.view.lkml\"` to ensure visibility of all views.\n\n"
                
                "   Context Tools:\n"
                "   - `get_explore_fields_from_context` (get fields from uncommitted LookML)\n"
                "   - `register_lookml_manually` (manual registration if auto-registration fails)\n\n"
                
                "   Visualization (for uncommitted LookML):\n"
                "   - `create_chart_from_context` (SINGLE visual - use for simple questions)\n"
                "   - `create_dashboard` + `add_dashboard_element` (MULTI-tile - use for dashboard requests)\n"
                "   - `create_dashboard_from_context` (alternative multi-tile approach)\n\n"
                
                "   Utilities:\n"
                "   - `search_web`, `get_connections`, `get_connection_tables`, etc.\n\n"
                
                "**REFUSAL PROTOCOL**:\n"
                "'I am in POC Mode and can only work with new/uncommitted LookML. To analyze existing data, please disable POC mode.'\n\n"
                
                "🚫 **LOOKML ARTIFACT NAMING PROTOCOL** (CRITICAL - PREVENTS HALLUCINATION):\\n"
                "1. **AUTO-REGISTRATION AWARENESS**:\\n"
                "   - When you call `create_project_file`, artifacts are AUTOMATICALLY registered.\\n"
                "   - Models via `connection:`, Explores via `explore: name`, Views via `view: name`.\\n"
                "   - You DO NOT need `get_git_branch_state` to find names you just created.\\n\\n"
                
                "2. **NAME LOCK MANDATE**:\\n"
                "   - IMMEDIATELY after creating a file, you MUST create a mental 'NAME LOCK'.\\n"
                "   - Extract exact names from the content YOU wrote.\\n"
                "   - THESE ARE THE ONLY NAMES THAT EXIST. Use them in all subsequent calls.\\n\\n"
                
                "3. **EXPLORE NAME vs BASE VIEW**:\\n"
                "   - ❌ WRONG: Using the name after `from:` (e.g., `from: users` -> explore='users')\\n"
                "   - ✅ CORRECT: Using the name after `explore:` (e.g., `explore: customer_analytics` -> explore='customer_analytics')\\n"
                "   - ALWAYS use the `explore:` name.\\n\\n"

                "🔒 **LOCKED SETTINGS PROTOCOL** (MANDATORY FOR POC DASHBOARDS):\n"
                "When creating a POC dashboard, you MUST implicitly use the 'settings' model if it exists.\n"
                "1. CHECK if `settings.model.lkml` exists (using get_project_files).\n"
                "2. IF IT EXISTS: You MUST use `model='settings'` for the dashboard tiles, NOT the business model.\n"
                "   - The `settings` model includes the business model but adds required context.\n"
                "   - ❌ Incorrect: `model='marketing'`\n"
                "   - ✅ Correct: `model='settings'` (assuming marketing is included in settings)\n"
                "3. IF NO settings model: Use the business model directly.\n\n"
                
                "🔒 **LOCKED DISCOVERY PROTOCOL** (MANDATORY):\\n\\n"
                "After calling get_connection_tables, you MUST:\\n"
                "1. Create locked inventory: '✅ LOCKED TABLES: [list exact names]'\\n"
                "2. State: '⚠️ ONLY these tables exist. Cannot reference others.'\\n"
                "3. If user mentions unlisted table: STOP and ASK for clarification\\n"
                "4. Before creating LookML: Verify table is in locked inventory\\n\\n"
                "❌ FORBIDDEN: Using tables from memory, context, or assumptions\\n"
                "✅ REQUIRED: ALL tables MUST come from get_connection_tables\\n\\n"
                
                "CRITICAL: DASHBOARD TILE CREATION PROTOCOL (PREVENTS INFINITE LOOPS)\\n\\n"

                "🚨 AFTER create_dashboard RETURNS SUCCESS:\\n"
                "1. ✅ Lock dashboard_id and base_url\\n"
                "2. ✅ Call get_explore_fields_from_context ONCE for the primary explore\\n"
                "3. ✅ CREATE A FIELD INVENTORY LIST (write it out):\\n"
                "   '📋 LOCKED FIELD INVENTORY:\\n"
                "    Dimensions: user.id, user.age, user.country, ...\\n"
                "    Measures: user.count, orders.total_revenue, ...'\\n"
                "   This inventory is your ONLY source of truth.\\n"
                "4. ✅ IMMEDIATELY start add_dashboard_element calls using ONLY fields from inventory\\n\\n"

                "❌ FORBIDDEN AFTER create_dashboard:\\n"
                "   - Creating new project files (you already created them!)\\n"
                "   - Calling create_project_file again\\n"
                "   - Going 'back' to LookML creation\\n"
                "   - Saying 'I need to create X view' (you already did!)\\n"
                "   - Circular verification loops\\n"
                "   - ⛔ **HALLUCINATING TILES**: You must verify `add_dashboard_element` returned success before claiming it.\\n"
                "   - Claiming 'Tile added' without an actual successful tool call.\\n\\n"

                "⚠️ IF get_explore_fields_from_context returns empty/error:\\n"
                "   - Call register_lookml_manually ONCE\\n"
                "   - Then proceed to add_dashboard_element\\n"
                "   - DO NOT create new files\\n\\n"

                "🔒 RULE: Once dashboard_id exists, you are in TILE ASSEMBLY MODE\\n"
                "   - Your ONLY job: add_dashboard_element (6x) → create_dashboard_filter → present URL\\n"
                "   - NO file creation, NO model updates, NO going backwards\\n\\n"
                "⚖️ **UNIVERSAL VISUAL Q&A (MANDATORY)**:\\n"
                "   Before adding ANY tile, you MUST evaluate:\\n"
                "   1. Does the metric/dimension exist in the explore? (Check Locked Field Inventory)\\n"
                "   2. Does this visual format (Bar, Line, etc.) make sense for this specific data scope?\\n"
                "   3. Have I alternated visual types to avoid repetitive dashboards?\\n\\n"

                "🎨 **VALID LOOKER VIS TYPES (vis_config.type) — MANDATORY REFERENCE**:\\n"
                "   Always use EXACTLY one of these strings for `vis_config.type`:\\n"
                "   | Goal                  | vis_config.type       |\\n"
                "   |-----------------------|-----------------------|\\n"
                "   | Single KPI / metric   | single_value          |\\n"
                "   | Bar chart (vertical)  | looker_bar            |\\n"
                "   | Column chart (horiz)  | looker_column         |\\n"
                "   | Line chart            | looker_line           |\\n"
                "   | Area chart            | looker_area           |\\n"
                "   | Scatter plot          | looker_scatter        |\\n"
                "   | Pie chart             | looker_pie            |\\n"
                "   | Data table            | looker_grid           |\\n"
                "   | Funnel                | looker_funnel         |\\n"
                "   | Map (geographic)      | looker_google_map     |\\n"
                "   | Waterfall             | looker_waterfall      |\\n"
                "   ⛔ NEVER use 'looker_single_value' — use 'single_value' instead.\\n"
                "   ⛔ NEVER use a vis type not in this table.\\n\\n"
            )
        else:
            system_prompt += (
                "🌍 **PRODUCTION MODE**\n"
                "You have access to all tools. You can query existing models and build new ones.\n"
                "**PRIORITY**: Use production tools like `get_models` and `run_query` for existing data questions.\n\n"
                
                "❌ **HIDDEN/FORBIDDEN TOOLS** (POC Only):\n"
                "   - `get_explore_fields_from_context`\n"
                "   - `create_query_from_context`\n"
                "   - `create_chart_from_context`\n"
                "   - `create_dashboard_from_context`\n"
                "   - `register_lookml_manually`\n"
                "   These tools are for uncommitted LookML only. In Production Mode, use the standard API tools.\n\n"
            )

        # VISUALIZATION FORMATTING RULES (Applies to both modes)
        system_prompt += (
            "📊 **VISUALIZATION FORMATTING RULES** (CRITICAL):\n"
            "When a tool returns a URL (Explore, Dashboard, or Chart):\n"
            "1. **markdown Link ONLY**: `[Interactive Chart](https://.../embed/...)`\n"
            "2. **NO HTML**: Do NOT use `<iframe>`, `<embed>`, or `<object>` tags.\n"
            "   - The chat interface AUTOMATICALLY embeds Markdown links ending in `/embed/...`\n"
            "   - Using HTML tags will cause the code to display as raw text.\n"
            "3. **ALWAYS** provide the link. Never say \"I created it\" without showing the link.\n\n"
            "📝 **MANDATORY REPORTING FORMAT**:\n"
            "Every analysis (dashboard or single chart) MUST follow this structure:\n"
            "1. **Highlight / Insight 💡**: What happened? (Concise summary)\n"
            "2. **Trends / Context 📈**: How is it changing? (% change, benchmarks)\n"
            "3. **Recommendations 🚀**: Actionable next steps based on data.\n"
            "4. **Follow-up Questions ❓**: 2-3 logical next questions to deepen analysis.\n\n"
        )
        
        # SEARCH ERROR CHECKING
        system_prompt += (
            "RULE: MANDATORY WEB SEARCH ERROR CHECKING\n"
            "When search_web is called:\n"
            "1. Check response for \"error\" field\n"
            "2. If error=true, STOP and inform user:\n"
            "   \"❌ Web search unavailable: [reason]\"\n"
            "3. NEVER proceed with fabricated information\n"
            "4. Offer alternative: \"I can help with your internal data instead\"\n\n"
        )

        # UNIVERSAL PROTOCOLS
        system_prompt += (
            "CRITICAL: URL AND ID INTEGRITY PROTOCOL (PREVENTS HALLUCINATION)\n\n"
            
            "1. Call `create_dashboard` with title\\n"
            "2. EXTRACT and SAVE these values from the response:\\n"
            "   - `dashboard_id`: Use in ALL `add_dashboard_element` calls\\n"
            "   - `full_url`: Present ONLY after all tiles are added\\n\n"
            "🛡️ **CLARIFICATION MANDATE (UNIVERSAL)**:\n"
            "If a user request is ambiguous, lacking detail, or technically contradictory:\n"
            "- **STOP** immediately.\n"
            "- **ALWAYS** ask return clarifying questions before proceeding with tool calls.\n"
            "- **NEVER** guess user intent if the path is unclear.\n\n"
            "3. For each tile, call `add_dashboard_element` with the extracted `dashboard_id`\\n"
            "4. 🔒 MANDATORY: Call `create_dashboard_filter` to add at least ONE filter\\n"
            "   - Recommended: Date range filter (field: created_date, type: date)\\n"
            "   - Other options: Category filters, dimension filters\\n"
            "   - NEVER skip this step - filters improve user experience\\n"
            "5. Present to user: Use the `full_url` from step 2 (already contains /embed/)\\n"
            "   ⚠️ **CRITICAL RULE**: DO NOT present the dashboard URL unless you have successfully added at least one tile.\\n"
            "   - Check `add_dashboard_element` output for success.\\n"
            "   - If adding tiles fails, report the error instead of showing an empty dashboard.\\n\\n"
            
            "CRITICAL: AUTOMATIC QUERY VISUALIZATION PROTOCOL (MANDATORY FOR SINGLE QUERY REQUESTS)\\n\\n"

            "When user asks for data analysis that results in ONE query/visualization (not a dashboard):\\n"
            "STEP 1: Run the query using query tool to get data\\n"
            "STEP 2: IMMEDIATELY call query_url with IDENTICAL parameters to get embed URL\\n"
            "STEP 3: Extract the EXACT url field from response:\\n"
            "   ✅ DO: Use the exact string from response.url\\n"
            "   ❌ DON'T: Construct URLs, assume domains, or modify the returned URL\\n"
            "STEP 4: Present as Markdown link:\\n"
            "   Format: [Interactive Chart]({exact_url_from_response})\\n"
            "   The URL already contains /embed/ - use it AS-IS\\n"
            "STEP 5: Provide insights (4-section format)\\n\\n"

            "**URL INTEGRITY RULES (ZERO TOLERANCE):**\\n"
            "⛔ NEVER invent domain names (googledemo, looker-demo, etc.)\\n"
            "⛔ NEVER construct URLs from memory or patterns\\n"
            "⛔ NEVER use placeholder URLs\\n"
            "✅ ALWAYS extract from tool response fields\\n"
            "✅ ALWAYS verify you have the actual URL before presenting\\n\\n"

            "   - Other options: Category filters, dimension filters\\n"
            "   - NEVER skip this step - filters improve user experience\\n"
            "5. Present to user: Use the `full_url` from step 2 (already contains /embed/)\\n\\n"
            
            "**CRITICAL - EMBED URL REQUIREMENT:**\\n"
            "❌ NEVER use: `{base_url}/dashboards/{id}` (causes X-Frame-Options error)\\n"
            "✅ ALWAYS use: `{base_url}/embed/dashboards/{id}` (from full_url field)\\n"
            "The tool response includes `full_url` - USE IT DIRECTLY, don't construct your own!\\n\\n"
            
            "**CRITICAL - FILTER REQUIREMENT:**\\n"
            "❌ NEVER create dashboards without filters\\n"
            "✅ ALWAYS add at least 1 filter (date range recommended)\\n"
            "Filters enable users to explore data interactively - they are MANDATORY!\\n\\n"
            
            "**NEVER:**\n"
            "- Invent or guess dashboard IDs\n"
            "- Construct URLs using assumed domains\n"
            "- Use placeholder values like 'DASHBOARD_ID_HERE'\n\n"
            
            "**ALWAYS:**\n"
            "- Extract actual values from tool responses\n"
            "- Use the exact strings returned by tools\n"
            "- Verify you have the dashboard_id before calling add_dashboard_element\n\n"
            
            "CRITICAL: DATA ANALYSIS PROTOCOLS:\n"
            "1. **METADATA FIRST**: Before running ANY aggregate query, understand available measures.\n"
            "   - Call `get_explore_fields_from_context` (POC) or `get_dimensions`/`get_measures` (Production)\n"
            "   - DO NOT assume fields exist. Verify them first.\n\n"
            
            "2. **CLARIFY AMBIGUITY**: If user asks for 'best', 'top', 'worst', 'most' without specifying metric:\n"
            "   - **STOP** and **ASK**: 'Top 10 by which metric? (e.g. Count, Revenue, Margin?)'\n"
            "   - Do NOT guess the metric.\n\n"
            
            "CRITICAL: DATA PRESENTATION PROTOCOLS:\n"
            "**INSIGHTS FORMAT** (MANDATORY - ALL 4 SECTIONS REQUIRED):\n"
            "\n"
            "⚠️ EVERY response with data analysis MUST include ALL 4 sections:\n"
            "\n"
            "🔎 INSIGHTS (What happened?)\n"
            "   - Bottom-line business impact with numbers\n"
            "   - Quantified findings, no fluff\n"
            "   - Example: 'Revenue dropped 23% ($450K) in Q3 vs Q2.'\n"
            "   - Example: 'Top 3 customers account for 67% of revenue ($2.1M).'\n\n"
            
            "📊 TRENDS (Why did it happen?)\n"
            "   - Patterns, correlations, root causes\n"
            "   - Data-driven explanations\n"
            "   - Example: 'Mobile traffic +40%, but mobile conversion -35%.'\n"
            "   - Example: 'Churn spiked after pricing change (correlation: 0.89).'\n\n"
            
            "🎯 RECOMMENDATIONS (What should we do?)\n"
            "   - Specific, actionable steps\n"
            "   - Prioritized by estimated impact\n"
            "   - Example: '1. Fix mobile checkout (est. +$200K/mo) 2. A/B test pricing'\n"
            "   - Example: 'Launch retention campaign targeting high-value segment.'\n\n"
            
            "❓ FOLLOW-UP QUESTIONS (What should we explore next?)\n"
            "   - Deeper analysis opportunities\n"
            "   - Related metrics to investigate\n"
            "   - Example: 'Compare mobile vs desktop funnel drop-off by step.'\n"
            "   - Example: 'Analyze customer cohorts by acquisition channel.'\n\n"
            
            "❌ FORBIDDEN: Chart descriptions without analysis\n"
            "❌ FORBIDDEN: Missing any of the 4 sections\n"
            "✅ REQUIRED: Business insights with quantified impact\n\n"
            
            "CRITICAL: LOOKML FILE CREATION PROTOCOL:\n"
            "1. **ALWAYS** create LookML files at ROOT LEVEL using flat paths\n"
            "   - Views: `users.view.lkml` (NOT `_view` suffix)\n"
            "   - Models: `model_name.model.lkml`\n\n"
            
            "2. **create_project_file**: Use for NEW files and UPDATES\n"
            "   - Auto-registration happens automatically\n"
            "   - For updates, create new version (e.g. `users_v2.view.lkml`)\n\n"
            
            "CRITICAL: SELF-VERIFICATION PROTOCOL (PREVENTS ARTIFACT HALLUCINATION):\n"
            "Before calling add_dashboard_element:\n"
            "1. Call `get_git_branch_state` to see EXACT file names created\n"
            "2. Call `get_explore_fields_from_context` using EXACT model/explore names from files\n"
            "3. List out the verified names in a checklist:\n"
            "   ✓ Model name: [exact_name]\n"
            "   ✓ Explore name: [exact_name]\n"
            "   ✓ Available fields: [list]\n"
            "4. ONLY THEN proceed with dashboard creation using these VERIFIED names\n\n"
            
            "**NEVER reference LookML artifacts from memory - ALWAYS verify from tools first**\n\n"
            
            "CRITICAL: DASHBOARD ID STATE MANAGEMENT (PREVENTS ID HALLUCINATION):\n"
            "When creating dashboards:\n"
            "1. Call `create_dashboard` ONCE\n"
            "2. IMMEDIATELY after response, state: '✅ LOCKED: dashboard_id = [ID], base_url = [URL]'\n"
            "3. For ALL subsequent `add_dashboard_element` calls, prefix with: 'Using locked dashboard_id: [ID]'\n"
            "4. If you create a second dashboard, STOP and explain why the first failed\n"
            "5. NEVER create multiple dashboards without explicit user approval\n\n"
            
            "**Rule: ONE dashboard per request unless user asks for multiple**\n\n"
            
            "CRITICAL: MANDATORY FIELD VERIFICATION (NO EXCEPTIONS):\n"
            "\n"
            "⛔ STOP - READ THIS BEFORE ANY DASHBOARD/CHART CREATION:\n"
            "\n"
            "STEP 1: VERIFY FIELDS (REQUIRED)\n"
            "   POC Mode (uncommitted LookML): Call `get_explore_fields_from_context`\n"
            "   Production Mode: Call `get_explore_fields`\n"
            "\n"
            "STEP 2: CREATE VERIFICATION CHECKLIST\n"
            "   List EXACT field names you plan to use:\n"
            "   ✅ orders.count (verified in explore)\n"
            "   ✅ orders.total_revenue (verified in explore)\n"
            "   ✅ orders.created_date (verified in explore)\n"
            "\n"
            "STEP 3: USE ONLY VERIFIED FIELDS\n"
            "   ❌ FORBIDDEN: Inventing fields like 'revenue', 'sales', 'total'\n"
            "   ✅ REQUIRED: Using exact names from verification\n"
            "\n"
            "⛔ IF YOU SKIP VERIFICATION, THE TOOL WILL FAIL\n"
            "⛔ IF FIELD NOT IN VERIFIED LIST, STOP AND ASK USER\n\n"
            
            "VISUALIZATION TYPE CONFIGURATION:\n"
            "\n"
            "VALID TYPES & WHEN TO USE:\n"
            "   📈 looker_line: Time series, trends\n"
            "      - Requires: date dimension + measures\n"
            "      - Config: x_axis=[date], y_axis=[measures]\n"
            "\n"
            "   📊 looker_column: Comparisons, categories\n"
            "      - Requires: dimension + measures\n"
            "      - Config: x_axis=[dimension], y_axis=[measures]\n"
            "\n"
            "   📉 looker_bar: Rankings, horizontal comparisons\n"
            "      - Requires: dimension + measures\n"
            "      - Config: x_axis=[measures], y_axis=[dimension]\n"
            "\n"
            "   🥧 looker_pie: Part-to-whole (MAX 7 slices)\n"
            "      - Requires: 1 dimension + 1 measure\n"
            "      - Config: dimension=[category], measure=[value]\n"
            "      - If >7 categories, use TOP 7 or choose different viz\n"
            "\n"
            "   📋 looker_grid: Tables, detailed data\n"
            "      - Use for: raw data, multiple dimensions\n"
            "\n"
            "   🎯 looker_single_value: KPIs, single metrics\n"
            "      - Requires: ONLY 1 measure, NO dimensions\n"
            "      - Config: measure=[single_metric]\n\n"
            
            "**CRITICAL: KEEP IT BRIEF**\n"
            "- Do NOT explain thought process unless asked\n"
            "- Do NOT say 'I will now run...'. JUST RUN THE TOOL.\n"
        )
        
        if explore_context and not poc_mode:
            system_prompt += f"\\n**Context**: {explore_context}\\n"
            
        return system_prompt

    # ==========================================
    # MODEL PROCESSING
    # ==========================================

    async def _process_with_gemini(
        self, 
        user_message: str, 
        history: List[Dict[str, str]], 
        tools: List[Dict[str, Any]], 
        looker_url: str, 
        client_id: str, 
        client_secret: str, 
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        """Process message with Gemini (action-first, JSON-based)."""
        
        gemini_instruction = (
            f"{system_prompt}\\n\\n"
            "### MANDATORY OUTPUT PROTOCOL:\\n"
            '1. Output a raw JSON object to call a tool: {"tool": "name", "arguments": {...}}\\n'
            "2. DO NOT give a text answer until you have analyzed tool results.\\n"
            "3. NO Python code, NO markdown blocks. ONLY RAW JSON."
        )

        contents = []
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            
            # If the frontend sent rich parts, convert them to text for Gemini
            if "parts" in msg and msg["parts"]:
                text_parts = []
                for p in msg["parts"]:
                    if p["type"] == "text":
                        text_parts.append(p["content"])
                    elif p["type"] == "tool":
                        if p.get("status") == "running":
                             text_parts.append(f"[Attempted to use tool '{p.get('tool')}' with input {p.get('input')} but the user aborted the request before it finished.]")
                        elif p.get("status") == "success":
                             text_parts.append(f"[Successfully used tool '{p.get('tool')}' with input {p.get('input')}. Result: {p.get('result')}]")
                
                if text_parts:
                     contents.append({"role": role, "parts": [{"text": "\n".join(text_parts)}]})
                else:
                     contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            else:
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
                
        contents.append({
            "role": "user", 
            "parts": [{"text": f"{gemini_instruction}\\n\\nUSER REQUEST: {user_message}"}]
        })
        
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {
                cat: HarmBlockThreshold.BLOCK_NONE 
                for cat in [
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH, 
                    HarmCategory.HARM_CATEGORY_HARASSMENT, 
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, 
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
                ]
            }
            
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
                        raw_result = await self.execute_tool(
                            t_name, 
                            data.get("arguments", {}), 
                            looker_url, 
                            client_id, 
                            client_secret
                        )
                        
                        # Serialize result safely
                        if isinstance(raw_result, dict) and "result" in raw_result:
                            res = raw_result["result"]
                            safe_result = json.dumps(res) if isinstance(res, (dict, list)) else str(res)
                        else:
                            safe_result = str(raw_result)
                            
                        tool_calls.append({
                            "tool": t_name, 
                            "arguments": data.get("arguments", {}), 
                            "result": safe_result
                        })
                except json.JSONDecodeError:
                    pass

            if tool_calls:
                summary_prompt = (
                    f"CONTEXT: {system_prompt}\\n"
                    f"REQUEST: {user_message}\\n"
                    f"TOOL RESULT: {tool_calls[0]['result']}\\n\\n"
                    f"Answer using this data."
                )
                final_text = self.model.generate_content(summary_prompt).text
                return {"success": True, "response": final_text, "tool_calls": tool_calls}
            
            return {"success": True, "response": raw_text, "tool_calls": []}
        except Exception as e:
            return {"success": False, "response": f"Error: {str(e)}", "tool_calls": []}

    async def _process_with_claude(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        looker_url: str,
        client_id: str,
        client_secret: str,
        system_prompt: str = "",
        images: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process message with Claude (streaming, tool use)."""
        
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
            
            # If the frontend sent rich parts, convert them to Claude's format
            if "parts" in msg and msg["parts"]:
                claude_parts = []
                has_running_tool = False
                for p in msg["parts"]:
                    if p["type"] == "text":
                        claude_parts.append({"type": "text", "text": p["content"]})
                    elif p["type"] == "tool":
                        # If it's a running tool (from an aborted stream), we MUST close it cleanly
                        # Claude API requires tool_use -> tool_result pairs.
                        # We convert aborted tools into text to prevent API errors about missing results,
                        # while still giving Claude context that a tool was attempted but aborted.
                        if p.get("status") == "running":
                             has_running_tool = True
                             claude_parts.append({
                                 "type": "text", 
                                 "text": f"\[Attempted to use tool '{p.get('tool')}' with input {p.get('input')} but the user aborted the request before it finished.\]"
                             })
                        elif p.get("status") == "success":
                             # Technically we should rebuild the entire tool_use/tool_result chain for Claude
                             # but for now, if it succeeded historically, we just add it as text context
                             # to avoid strictly managing tool_call_ids across sessions.
                             claude_parts.append({
                                 "type": "text", 
                                 "text": f"\[Successfully used tool '{p.get('tool')}' with input {p.get('input')}. Result: {p.get('result')}\]"
                             })
                
                if claude_parts:
                     messages.append({"role": role, "content": claude_parts})
                else:
                     messages.append({"role": role, "content": msg["content"]})
                     
            else:
                # Fallback for plain text messages
                messages.append({"role": role, "content": msg["content"]})
            
        # Build user message with images if provided
        if images and len(images) > 0:
            # Format message with images for Claude vision API
            content_parts = []
            
            # Add images first
            for img_data in images:
                # Remove data URL prefix if present
                if img_data.startswith('data:image'):
                    # Extract base64 data and media type
                    header, base64_data = img_data.split(',', 1)
                    media_type = header.split(';')[0].split(':')[1]  # e.g., "image/jpeg"
                else:
                    # Assume it's already base64
                    base64_data = img_data
                    media_type = "image/jpeg"  # Default
                
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data
                    }
                })
            
            # Add text message
            content_parts.append({
                "type": "text",
                "text": user_message
            })
            
            messages.append({"role": "user", "content": content_parts})
        else:
            # No images, just text
            messages.append({"role": "user", "content": user_message})

        try:
            max_turns = 10
            last_activity = __import__('time').time()  # Track last activity for keepalive
            
            for turn in range(max_turns):
                logger.info(f"Claude Turn {turn + 1}/{max_turns}")
                
                # Use streaming API to prevent timeout issues with long responses
                async with self.client.messages.stream(
                    model=self.model_name,
                    max_tokens=20000,  # Reduced from 30K to 20K for better performance
                    system=system_prompt,
                    messages=messages,
                    tools=claude_tools
                ) as stream:
                    # Stream text in real-time
                    async for text in stream.text_stream:
                        yield {"type": "text", "content": text}
                        last_activity = __import__('time').time()  # Update activity time
                    
                    # Get final message with tool calls
                    response = await stream.get_final_message()
                
                logger.info(f"Stop Reason: {response.stop_reason}")
                
                turn_tool_blocks = []
                
                # Process tool calls from final message (text already streamed)
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        logger.info(f"Tool Use: {content_block.name}")
                        turn_tool_blocks.append(content_block)
                        yield {
                            "type": "tool_use",
                            "tool": content_block.name,
                            "input": content_block.input
                        }
                
                if not turn_tool_blocks:
                    logger.info("No tool calls. Stopping.")
                    break
                
                # Execute tools
                tool_results = []
                for tool_block in turn_tool_blocks:
                    # Send keepalive if no activity for 20 seconds
                    if __import__('time').time() - last_activity > 20:
                        yield {"type": "keepalive"}
                        last_activity = __import__('time').time()
                    
                    logger.info(f"Executing: {tool_block.name}")
                    tool_result = await self.execute_tool(
                        tool_block.name,
                        tool_block.input,
                        looker_url,
                        client_id,
                        client_secret
                    )
                    
                    last_activity = __import__('time').time()  # Update after tool execution
                    
                    # Serialize result
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

                # HALLUCINATION CHECK (Fix #2)
                # If checking specifically for dashboard tiles
                actual_add_calls = sum(1 for b in turn_tool_blocks if b.name == "add_dashboard_element")
                
                # Check for hallucinations in text blocks
                text_content = ""
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text
                
                if actual_add_calls == 0:
                    # Logic removed per user request (Reference: User Request 633)
                    pass
                
                # Update conversation history
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                
        except Exception as e:
            logger.error(f"Claude error: {e}")
            yield {"type": "error", "content": str(e)}

    # ==========================================
    # MAIN ENTRY POINT
    # ==========================================

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
        self.poc_mode = poc_mode  # Persist for tool checks
        logger.info(f"Processing message: {user_message[:50]}... (POC Mode: {poc_mode})")
        if images:
             logger.info(f"Received {len(images)} images")
        
        # Get tools (filtered by POC mode)
        if available_tools is None:
            available_tools = await self.list_available_tools(
                looker_url, 
                client_id, 
                client_secret,
                poc_mode=poc_mode
            )

        # Build system prompt
        system_instruction = self._build_system_prompt(
            gcp_project=gcp_project,
            gcp_location=gcp_location,
            looker_url=looker_url,
            explore_context=explore_context,
            poc_mode=poc_mode
        )

        # Inject explore_context into user_message if provided
        full_message = user_message
        
        # FIX #3: Rigid Template Injection for Dashboard Creation
        if "dashboard" in user_message.lower() and "create" in user_message.lower():
             logger.info("Injecting Rigid Dashboard Template")
             dashboard_sequence = (
                "🛑 **INTERVENTION: DASHBOARD CREATION DETECTED**\n"
                "You MUST follow the MANDATORY DASHBOARD CREATION SEQUENCE:\n"
                "1. `create_dashboard` -> WAIT for ID.\n"
                "2. `add_dashboard_element` for EACH tile -> WAIT for success.\n"
                "3. `create_dashboard_filter` (Mandatory).\n"
                "4. ONLY THEN present the link.\n"
                "⛔ DO NOT claim tiles are added unless you actually call the tool.\n\n"
             )
             full_message = f"{dashboard_sequence}\nUSER REQUEST: {user_message}"
        
        if explore_context:
            full_message = f"CONTEXT:\\n{explore_context}\\n\\n{full_message}"

        try:
            if self.is_claude:
                # Claude is a generator (streaming events)
                async for event in self._process_with_claude(
                    full_message, history, available_tools,
                    looker_url, client_id, client_secret,
                    system_prompt=system_instruction,
                    images=images
                ):
                    yield event
            else:
                # Gemini is request-response, bridge to events
                result = await self._process_with_gemini(
                    full_message, history, available_tools,
                    looker_url, client_id, client_secret,
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
