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

GLOBAL_LOOKML_CONTEXT = LookMLContext() if LookMLContext else None

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
    "search_web"                        # External context/research
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
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.created_files_cache = {}
        
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
            return self._execute_search_web(arguments)
        
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
                 
            # Resolve deploy_lookml.py path correctly
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
            
            return {
                "success": True,
                "result": {
                    "dashboard_id": dashboard.id,
                    "base_url": base_url,
                    "full_url": full_url,
                    "title": dashboard.title,
                    "message": f"Dashboard '{title}' created successfully. Use dashboard_id={dashboard.id} for add_dashboard_element calls."
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

    def _execute_search_web(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web."""
        try:
            query = args.get("query")
            if not query:
                return {"success": False, "error": "No query provided"}
            
            results = DDGS().text(query, max_results=5)
            
            return {
                "success": True,
                "result": results
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "error": str(e)}

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
        """Enhanced get_models that summarizes large lists."""
        try:
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
                formatted.append({
                    "name": m.name, 
                    "project_name": m.project_name, 
                    "explores": explores_summary
                })
            
            if not self.is_claude and len(formatted) > 30:
                summary_models = formatted[:30]
                summary_models.append({"message": f"... and {len(formatted) - 30} more models."})
                return {
                    "success": True, 
                    "workspace": workspace, 
                    "models": summary_models, 
                    "note": "Truncated for Gemini safety."
                }
            
            return {"success": True, "workspace": workspace, "models": formatted}
        except Exception as e:
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
                "If the user asks for existing/production data analysis, you MUST refuse and say:\n"
                "'I am in POC Mode and can only work with new/uncommitted LookML. To analyze existing data, please disable POC mode.'\n\n"
            )
        else:
            system_prompt += (
                "🌍 **PRODUCTION MODE**\n"
                "You have access to all tools. You can query existing models and build new ones.\n"
                "**PRIORITY**: Use production tools like `get_models` and `run_query` for existing data questions.\n\n"
            )

        # UNIVERSAL PROTOCOLS
        system_prompt += (
            "CRITICAL: URL AND ID INTEGRITY PROTOCOL (PREVENTS HALLUCINATION)\n\n"
            
            "**DASHBOARD CREATION WORKFLOW:**\n"
            "1. Call `create_dashboard` with title\n"
            "2. EXTRACT and SAVE these values from the response:\n"
            "   - `dashboard_id`: Use in ALL `add_dashboard_element` calls\n"
            "   - `base_url`: Use to construct final URL\n"
            "3. For each tile, call `add_dashboard_element` with the extracted `dashboard_id`\n"
            "4. Present to user: `{extracted_base_url}/embed/dashboards/{extracted_dashboard_id}`\n\n"
            
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
            "**INSIGHTS FORMAT** (REQUIRED FOR ALL OUTPUTS):\n"
            "   🔎 INSIGHTS\n"
            "   - Bottom line impact (no descriptions)\n"
            "   - Example: 'Conversion dropped 15% in Q3 due to mobile checkout latency.'\n\n"
            
            "   📊 TRENDS\n"
            "   - What patterns drive this?\n"
            "   - Example: 'Mobile traffic up 40%, but conversion down 20%.'\n\n"
            
            "   🎯 RECOMMENDATIONS\n"
            "   - Actionable & specific steps\n"
            "   - Example: 'Revert checkout UI change and cache static assets.'\n\n"
            
            "   ❓ FOLLOW-UP QUESTIONS\n"
            "   - What to explore next\n"
            "   - Example: 'Compare mobile vs desktop funnel drop-off points.'\n\n"
            
            "**FORBIDDEN**: Do NOT simply describe charts. Provide ANALYSIS.\n\n"
            
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
            
            "CRITICAL: FIELD VALIDATION PROTOCOL (PREVENTS FIELD HALLUCINATION):\n"
            "Before creating ANY chart/dashboard tile:\n"
            "1. Call `get_explore_fields_from_context`\n"
            "2. Verify EVERY field you plan to use exists in the response\n"
            "3. If field missing, STOP and either:\n"
            "   a) Choose a different field that exists\n"
            "   b) Explain what's missing\n"
            "4. Create a field checklist:\n"
            "   Fields to use: [list]\n"
            "   ✓ Verified in explore: [yes/no for each]\n\n"
            
            "**NEVER assume a field exists - ALWAYS verify first**\n\n"
            
            "**CRITICAL: KEEP IT BRIEF**\n"
            "- Do NOT explain thought process unless asked\n"
            "- Do NOT say 'I will now run...'. JUST RUN THE TOOL.\n"
        )
        
        if explore_context:
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

        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} 
            for m in history
        ]
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
        system_prompt: str = ""
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
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            max_turns = 10
            
            for turn in range(max_turns):
                logger.info(f"Claude Turn {turn + 1}/{max_turns}")
                
                response = await self.client.messages.create(
                    model=self.model_name,
                    max_tokens=16000,
                    system=system_prompt,
                    messages=messages,
                    tools=claude_tools
                )
                
                logger.info(f"Stop Reason: {response.stop_reason}")
                
                turn_tool_blocks = []
                
                # Yield text and identify tool use
                for content_block in response.content:
                    if content_block.type == "text":
                        yield {"type": "text", "content": content_block.text}
                        
                    elif content_block.type == "tool_use":
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
                    logger.info(f"Executing: {tool_block.name}")
                    tool_result = await self.execute_tool(
                        tool_block.name,
                        tool_block.input,
                        looker_url,
                        client_id,
                        client_secret
                    )
                    
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
        if explore_context:
            full_message = f"CONTEXT:\\n{explore_context}\\n\\nUSER REQUEST: {user_message}"

        try:
            if self.is_claude:
                # Claude is a generator (streaming events)
                async for event in self._process_with_claude(
                    full_message, history, available_tools,
                    looker_url, client_id, client_secret,
                    system_prompt=system_instruction
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
