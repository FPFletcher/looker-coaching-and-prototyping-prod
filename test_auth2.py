import os
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account

try:
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    
    # Force refresh to get token
    credentials.refresh(Request())
    
    print(f"Project: {project}")
    print(f"Has Token: {credentials.token is not None}")
    if hasattr(credentials, 'service_account_email'):
        print(f"Service Account: {credentials.service_account_email}")
        
    print(f"Valid: {credentials.valid}")
except Exception as e:
    print(f"Auth Error: {e}")
