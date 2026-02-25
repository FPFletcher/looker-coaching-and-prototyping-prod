import os
from google.auth import default

try:
    credentials, project = default()
    print(f"Auth Success! Type: {type(credentials)}")
    print(f"Project: {project}")
    
    if hasattr(credentials, 'service_account_email'):
        print(f"Service Account: {credentials.service_account_email}")
    else:
        print("Using User/End-User ADC (requires gcloud auth application-default login)")
except Exception as e:
    print(f"Auth Error: {e}")
