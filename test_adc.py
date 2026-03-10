import google.auth
from google.auth.transport.requests import Request

try:
    credentials, project_id = google.auth.default()
    credentials.refresh(Request())
    print("ADC works! Access token:", credentials.token[:10] + "...")
except Exception as e:
    print("ADC Failed:", type(e).__name__, str(e))
