import sys
from google.oauth2 import id_token
from google.auth.transport import requests

# Make up an invalid token or mock one
token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.1234567890abcdef1234567890abcdef1234567890abc"

try:
    idinfo = id_token.verify_oauth2_token(token, requests.Request(), "test_client_id")
    print(idinfo)
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"Other exception: {e}")
