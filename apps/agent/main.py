import os
from dotenv import load_dotenv

# Load .env from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import logging

try:
    from .mcp_agent import MCPAgent
    from .chat_history import ChatHistoryManager, GoogleOAuthHandler
except ImportError:
    from mcp_agent import MCPAgent
    from chat_history import ChatHistoryManager, GoogleOAuthHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Looker MCP Chat API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for Cloud Run/POC
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_trace = traceback.format_exc()
    logger.error(f"GLOBAL UNHANDLED EXCEPTION for {request.url.path}: {str(exc)}\n{error_trace}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}", "trace": error_trace}
    )

# Optionally handle validation errors explicitly if we want
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Initialize agent - Global for stateless ops, but preferred to be per-request
# agent = MCPAgent()

# Initialize chat history manager
chat_manager = ChatHistoryManager()

# In-memory session storage (in production, use Redis or similar)
sessions = {}
looker_tools_cache = {}


class LookerCredentials(BaseModel):
    url: str
    client_id: str
    client_secret: str

class ConfigureRequest(BaseModel):
    credentials: LookerCredentials
    session_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, Any]] = []  # Changed from Dict[str, str] to support parts
    credentials: LookerCredentials
    model: str = "gemini-2.0-flash"  # Default model
    session_id: Optional[str] = None
    images: Optional[List[str]] = None  # Base64 encoded images
    explore: Optional[Dict[str, str]] = None  # Selected explore {name, label, model}
    gcp_project: Optional[str] = None
    gcp_location: Optional[str] = None
    poc_mode: bool = False  # New flag for strict POC mode
    vertex_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    use_vertex: bool = True

class ResetRequest(BaseModel):
    session_id: str

@app.get("/")
async def root():
    return {"message": "Looker MCP Chat API", "status": "running"}

@app.get("/api/sys/info")
def sys_info():
    import os
    import urllib.request
    import google.auth
    from google.oauth2 import service_account
    info = {"env": {k: v for k, v in os.environ.items() if "KEY" not in k and "SECRET" not in k}}
    try:
        credentials, project = google.auth.default()
        info["adc_type"] = str(type(credentials))
        info["adc_project"] = project
        if hasattr(credentials, "service_account_email"):
            info["sa_email"] = credentials.service_account_email
    except Exception as e:
        info["adc_error"] = str(e)
        
    try:
        url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        req = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=5) as response:
            info["metadata_token"] = response.read().decode()[:20] + "..."
    except Exception as e:
        info["metadata_error"] = str(e)
        if hasattr(e, 'read'):
            info["metadata_body"] = e.read().decode()

    return info

@app.get("/api/sys/fs")
def test_fs():
    import firebase_admin
    from firebase_admin import firestore
    try:
        import traceback
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        db = firestore.client()
        docs = db.collection('chat_sessions').limit(1).get()
        return {"success": True, "ids": [doc.id for doc in docs]}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
async def configure_looker(request: ConfigureRequest):
    """
    Validates Looker credentials and returns available MCP tools.
    """
    try:
        creds = request.credentials
        session_id = request.session_id or "default"
        
        # Instantiate session-specific agent
        agent = MCPAgent(session_id=session_id)
        
        tools = await agent.list_available_tools(
            creds.url,
            creds.client_id,
            creds.client_secret
        )
        
        return {
            "success": True,
            "message": f"Connected to Looker. Found {len(tools)} available tools.",
            "tools": tools
        }
    except Exception as e:
        logger.exception("Configuration failed")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint (Streaming).
    Processes user message and yields Server-Sent Events (SSE).
    """
    try:
        # Get or create session
        session_id = request.session_id or "default"
        if session_id not in sessions:
            sessions[session_id] = {
                "history": []
            }
        
        # Determine effective key for Gemini based on use_vertex flag
        effective_gemini_key = request.vertex_api_key
        if not request.use_vertex:
             effective_gemini_key = request.google_api_key

        # Instantiate agent
        # Instantiate agent
        logger.info(f"--- Chat Request ---")
        logger.info(f"Session: {session_id}, Model: {request.model}")
        logger.info(f"Use Vertex: {request.use_vertex}")
        logger.info(f"Vertex Key Provided: {'Yes' if request.vertex_api_key else 'No'} (Len: {len(request.vertex_api_key) if request.vertex_api_key else 0})")
        logger.info(f"Google API Key (Env): {'Yes' if os.environ.get('GOOGLE_API_KEY') else 'No'} (Len: {len(os.environ.get('GOOGLE_API_KEY', ''))})")
        logger.info(f"Anthropic Key Provided: {'Yes' if request.claude_api_key else 'No'} (Len: {len(request.claude_api_key) if request.claude_api_key else 0})")
        
        # Check credentials file
        sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if sa_path:
            logger.info(f"GOOGLE_APPLICATION_CREDENTIALS set to: {sa_path}")
            if os.path.exists(sa_path):
                 logger.info(f"Creds file exists at {sa_path}")
            else:
                 logger.error(f"Creds file MISSING at {sa_path}")
        else:
             logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set")
        
        chat_agent = MCPAgent(
            session_id=session_id, 
            model_name=request.model,
            vertex_api_key=effective_gemini_key or "",
            claude_api_key=request.claude_api_key or "",
            # llm_region removed as it was deprecated
        )

        async def event_generator():
            try:
                # Build system prompt with explore context if provided
                system_context = ""
                if request.explore:
                    system_context = f"\n\nUser has selected the explore: {request.explore['label']} (model: {request.explore['model']}, name: {request.explore['name']}). Use this explore for queries when relevant."
                
                # Use the agent's generator
                async for event in chat_agent.process_message(
                    request.message,
                    request.conversation_history or [],
                    request.credentials.url,
                    request.credentials.client_id,
                    request.credentials.client_secret,
                    images=request.images,
                    explore_context=system_context,
                    gcp_project=request.gcp_project or "",
                    gcp_location=request.gcp_location or "",
                    poc_mode=request.poc_mode
                ):
                    # Format as SSE
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                err_event = {"type": "error", "content": str(e)}
                yield f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream; charset=utf-8")

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset_session")
async def reset_session(request: ResetRequest):
    """
    Clears conversation history for a session.
    """
    if request.session_id in sessions:
        del sessions[request.session_id]
    
    return {"success": True, "message": "Session reset"}

@app.post("/api/explores")
async def get_explores(request: Dict[str, Any]):
    """Fetch all available explores from Looker"""
    import looker_sdk
    
    credentials = request.get("credentials", {})
    
    # Set Looker credentials
    # Set Looker credentials
    # Fallback to server environment variables if request is missing them
    base_url = credentials.get("url") or os.getenv("LOOKERSDK_BASE_URL", "")
    client_id = credentials.get("client_id") or os.getenv("LOOKERSDK_CLIENT_ID", "")
    client_secret = credentials.get("client_secret") or os.getenv("LOOKERSDK_CLIENT_SECRET", "")
    
    logger.info(f"DEBUG: Processing URL: {base_url}")

    logger.info(f"DEBUG: get_explores using URL: {base_url} | Client ID: {client_id[:5]}*** (Fallback active)")
    
    os.environ["LOOKERSDK_BASE_URL"] = base_url
    os.environ["LOOKERSDK_CLIENT_ID"] = client_id
    os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
    os.environ["LOOKERSDK_VERIFY_SSL"] = "false" # POC dev/test
    # Force API 4.0 initially
    os.environ["LOOKERSDK_API_VERSION"] = "4.0"
    
    try:
        sdk = None
        try:
            from looker_sdk import init40
            logger.info(f"DEBUG: Attempting init40 with URL: {base_url}")
            sdk = init40()
            me = sdk.me()
            logger.info(f"DEBUG: SDK 4.0 Initialized. Connected as {me.display_name}")
        except Exception as e_40:
            logger.error(f"❌ API 4.0 Init Failed: {str(e_40)}")
            # Raise or pass - for now pass so we return empty list
            pass

        if sdk:
            # Get all models with explicit fields to ensure explores are returned
            models = sdk.all_lookml_models(fields="name,label,project_name,explores(name,label)")
            
            explores_list = []
            for model in models:
                if model.explores:
                    for explore in model.explores:
                        explores_list.append({
                            "name": explore.name,
                            "label": explore.label or explore.name,
                            "model": model.name
                        })
            
            logger.info(f"✅ /api/explores: Returning {len(explores_list)} explores from {len(models)} models.")
            return {"explores": explores_list}
        else:
             return {"explores": []}

    except Exception as e:
        logger.error(f"Failed to fetch explores (returning empty list to prevent crash): {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"explores": []}

@app.post("/api/auth/google")
async def google_auth(request: Dict[str, Any]):
    """Authenticate user with Google OAuth token"""
    try:
        token = request.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="No token provided")
        
        # Initialize OAuth handler
        # Use fallback Client ID if env var is missing (matches frontend)
        client_id = os.getenv("GOOGLE_CLIENT_ID") or "826056756274-7653f7jteulh4en41u5oiupqe2stur2s.apps.googleusercontent.com"
        
        oauth_handler = GoogleOAuthHandler(
            client_id=client_id,
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "")
        )
        
        # Verify token
        user_info = oauth_handler.verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Create or update user
        oauth_handler.create_or_update_user(user_info)
        
        return {"user": user_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/test2")
async def test_auth_trace(request: Dict[str, Any]):
    try:
        token = request.get("token")
        from google.oauth2 import id_token
        from google.auth.transport import requests
        client_id = "826056756274-7653f7jteulh4en41u5oiupqe2stur2s.apps.googleusercontent.com"
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        return {"success": True, "idinfo": idinfo}
    except Exception as e:
        import traceback
        return {"error_type": str(type(e)), "error": str(e), "trace": traceback.format_exc()}

@app.post("/api/history/sessions")
async def get_sessions(request: Dict[str, Any]):
    """Get all chat sessions for a user"""
    try:
        user_id = request.get("user_id")
        if not user_id:
            return {"error": "No user_id provided"}
        
        sessions = chat_manager.get_user_sessions(user_id)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to get sessions: {str(e)}")
        return {"error": str(e)}

@app.post("/api/history/create")
async def create_session(request: Dict[str, Any]):
    """Create a new chat session"""
    try:
        user_id = request.get("user_id")
        title = request.get("title", "New Chat")
        
        if not user_id:
            return {"error": "No user_id provided"}
        
        session_id = chat_manager.create_session(user_id, title)
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        return {"error": str(e)}

@app.post("/api/history/messages")
async def get_messages(request: Dict[str, Any]):
    """Get all messages from a session"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            return {"error": "No session_id provided"}
        
        messages = chat_manager.get_session_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        return {"error": str(e)}

@app.post("/api/history/delete")
async def delete_session(request: Dict[str, Any]):
    """Delete a chat session"""
    try:
        session_id = request.get("session_id")
        user_id = request.get("user_id")
        
        if not session_id or not user_id:
            return {"error": "Missing session_id or user_id"}
        
        success = chat_manager.delete_session(session_id, user_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        return {"error": str(e)}

@app.post("/api/history/update_title")
async def update_title(request: Dict[str, Any]):
    """Update session title"""
    try:
        session_id = request.get("session_id")
        user_id = request.get("user_id")
        title = request.get("title")
        
        if not all([session_id, user_id, title]):
            return {"error": "Missing required parameters"}
        
        success = chat_manager.update_session_title(session_id, user_id, title)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to update title: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=False)
