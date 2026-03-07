"""
Google OAuth and Chat History Implementation (Firestore Backend)

This module provides OAuth authentication and chat history management using Google Cloud Firestore.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import Optional, List, Dict
import uuid

# Initialize Firebase Admin SDK
# Use Application Default Credentials (ADC) which works on Cloud Run (with SA) and Local (with gcloud auth)
try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"Warning: Failed to initialize Firestore: {e}")
    db = None

class ChatHistoryManager:
    """Manage chat history storage and retrieval using Firestore"""
    
    def __init__(self):
        # Firestore is initialized at module level to reuse connection
        pass
    
    def _ensure_db(self):
        if not db:
            raise Exception("Firestore client not initialized")
    
    def create_session(self, user_id: str, title: str = "New Chat") -> str:
        """Create a new chat session"""
        self._ensure_db()
        session_id = str(uuid.uuid4())
        
        doc_ref = db.collection('chat_sessions').document(session_id)
        doc_ref.set({
            'id': session_id,
            'user_id': user_id,
            'title': title,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return session_id
    
    def save_message(self, session_id: str, role: str, content: str):
        """Save a message to a session"""
        self._ensure_db()
        
        # Add message to 'messages' collection
        # Note: We use a top-level collection for easier querying, but link via session_id
        db.collection('messages').add({
            'session_id': session_id,
            'role': role,
            'content': content,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        # Update session updated_at
        session_ref = db.collection('chat_sessions').document(session_id)
        session_ref.update({
            'updated_at': firestore.SERVER_TIMESTAMP
        })
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a session"""
        self._ensure_db()
        
        # Query messages by session_id
        try:
            query = db.collection('messages').where('session_id', '==', session_id).order_by('created_at')
            docs = query.stream()
            
            messages = []
            for doc in docs:
                data = doc.to_dict()
                # Convert timestamp to string if needed, or keep object
                # The frontend expects 'created_at'. We'll return it as is or ISO string.
                created_at = data.get('created_at')
                if created_at:
                    # Firestore Timestamp to ISO string for JSON serialization
                    created_at = created_at.isoformat()
                
                messages.append({
                    "role": data.get('role'),
                    "content": data.get('content'),
                    "created_at": created_at
                })
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            # Fallback if index missing or error
            return []

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        self._ensure_db()
        
        try:
            query = db.collection('chat_sessions').where('user_id', '==', user_id).order_by('updated_at', direction=firestore.Query.DESCENDING)
            docs = query.stream()
            
            sessions = []
            for doc in docs:
                data = doc.to_dict()
                created_at = data.get('created_at')
                updated_at = data.get('updated_at')
                
                sessions.append({
                    "id": data.get('id'),
                    "title": data.get('title'),
                    "created_at": created_at.isoformat() if created_at else None,
                    "updated_at": updated_at.isoformat() if updated_at else None
                })
            return sessions
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (with user authorization check)"""
        self._ensure_db()
        
        # Verify ownership
        session_ref = db.collection('chat_sessions').document(session_id)
        doc = session_ref.get()
        
        if not doc.exists:
            return False
        
        data = doc.to_dict()
        if data.get('user_id') != user_id:
            return False
        
        # Delete session
        session_ref.delete()
        
        # Delete messages (Batch delete is better but for now loop)
        # Note: Firestore doesn't cascade delete. We must query and delete.
        messages = db.collection('messages').where('session_id', '==', session_id).stream()
        batch = db.batch()
        count = 0
        for msg in messages:
            batch.delete(msg.reference)
            count += 1
            if count >= 400: # Batch limit
                batch.commit()
                batch = db.batch()
                count = 0
        if count > 0:
            batch.commit()
            
        return True
    
    def update_session_title(self, session_id: str, user_id: str, title: str) -> bool:
        """Update session title (with user authorization)"""
        self._ensure_db()
        
        session_ref = db.collection('chat_sessions').document(session_id)
        doc = session_ref.get()
        
        if not doc.exists:
            return False
            
        if doc.to_dict().get('user_id') != user_id:
            return False
            
        session_ref.update({'title': title})
        return True

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
            
            # For Firestore, we typically use 'sub' as user ID
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
        """Create or update user in Firestore"""
        if not db: 
            return
            
        user_ref = db.collection('users').document(user_info["id"])
        user_ref.set({
            'id': user_info["id"],
            'email': user_info["email"],
            'name': user_info.get("name"),
            'picture': user_info.get("picture"),
            # Merge to avoid overwriting created_at unless we track it
            'last_login': firestore.SERVER_TIMESTAMP
        }, merge=True)
