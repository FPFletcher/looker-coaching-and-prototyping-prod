"""
Google OAuth and Chat History Implementation

This module provides OAuth authentication and chat history management.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3
from pathlib import Path

# Database setup
DB_PATH = Path(__file__).parent / "chat_history.db"

def init_database():
    """Initialize SQLite database for chat history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create chat sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        )
    """)
    
    conn.commit()
    conn.close()

class ChatHistoryManager:
    """Manage chat history storage and retrieval"""
    
    def __init__(self):
        init_database()
    
    def create_session(self, user_id: str, title: str = "New Chat") -> str:
        """Create a new chat session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (?, ?, ?)",
            (session_id, user_id, title)
        )
        conn.commit()
        conn.close()
        
        return session_id
    
    def save_message(self, session_id: str, role: str, content: str):
        """Save a message to a session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        # Update session updated_at
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        )
        messages = [
            {"role": row[0], "content": row[1], "created_at": row[2]}
            for row in cursor.fetchall()
        ]
        conn.close()
        return messages
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, title, created_at, updated_at 
               FROM chat_sessions 
               WHERE user_id = ? 
               ORDER BY updated_at DESC""",
            (user_id,)
        )
        sessions = [
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return sessions
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (with user authorization check)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify ownership
        cursor.execute(
            "SELECT user_id FROM chat_sessions WHERE id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        
        if not result or result[0] != user_id:
            conn.close()
            return False
        
        # Delete messages first (foreign key constraint)
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def update_session_title(self, session_id: str, user_id: str, title: str) -> bool:
        """Update session title (with user authorization)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE chat_sessions SET title = ? WHERE id = ? AND user_id = ?",
            (title, session_id, user_id)
        )
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success

class GoogleOAuthHandler:
    """Handle Google OAuth authentication"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify Google OAuth token and return user info"""
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), self.client_id
            )
            
            return {
                "id": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture")
            }
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None
    
    def create_or_update_user(self, user_info: Dict):
        """Create or update user in database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO users (id, email, name, picture) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(email) DO UPDATE SET
               name = excluded.name,
               picture = excluded.picture""",
            (user_info["id"], user_info["email"], 
             user_info.get("name"), user_info.get("picture"))
        )
        
        conn.commit()
        conn.close()
