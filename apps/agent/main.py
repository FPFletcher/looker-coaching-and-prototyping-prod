import os
from dotenv import load_dotenv

# Load .env from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from fastapi import FastAPI, HTTPException
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

# Initialize agent
agent = MCPAgent()

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
    gcp_project: Optional[str] = None
    gcp_location: Optional[str] = None
    poc_mode: bool = False  # New flag for strict POC mode

class ResetRequest(BaseModel):
    session_id: str

@app.get("/")
async def root():
    return {"message": "Looker MCP Chat API", "status": "running"}

@app.post("/api/configure_looker")
async def configure_looker(request: ConfigureRequest):
    """
    Validates Looker credentials and returns available MCP tools.
    """
    try:
        creds = request.credentials
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
        
        # Instantiate agent
        chat_agent = MCPAgent(model_name=request.model)

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
    os.environ["LOOKERSDK_BASE_URL"] = credentials.get("url", "")
    os.environ["LOOKERSDK_CLIENT_ID"] = credentials.get("client_id", "")
    os.environ["LOOKERSDK_CLIENT_SECRET"] = credentials.get("client_secret", "")
    os.environ["LOOKERSDK_VERIFY_SSL"] = "false" # POC dev/test
    
    try:
        sdk = looker_sdk.init40()
        
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
        
        return {"explores": explores_list}

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
            return {"error": "No token provided"}
        
        # Initialize OAuth handler
        oauth_handler = GoogleOAuthHandler(
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "")
        )
        
        # Verify token
        user_info = oauth_handler.verify_token(token)
        if not user_info:
            return {"error": "Invalid token"}
        
        # Create or update user
        oauth_handler.create_or_update_user(user_info)
        
        return {"user": user_info}
    except Exception as e:
        logger.error(f"Google auth failed: {str(e)}")
        return {"error": str(e)}

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
