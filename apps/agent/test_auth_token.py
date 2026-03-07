from google import genai
from google.oauth2 import credentials
try:
    token = 'AQ.Ab8RN6J-O6ePzzS-n-dzzojPT3lneGuZX0zgskLL7FFE6cULuQ'
    creds = credentials.Credentials(token)
    client = genai.Client(vertexai=True, project='antigravity-innovations', location='europe-west1', credentials=creds)
    # Just inspect, don't run query that would error due to token being generic
    print("Initialize success")
except Exception as e:
    import traceback
    traceback.print_exc()
