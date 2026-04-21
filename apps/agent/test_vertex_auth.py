import os
import json
import traceback
from google import genai
from google.oauth2 import credentials as oauth_credentials

def main():
    token = 'AQ.Ab8RN6Jv1IUeOiEpY2dmAkD6PZeXkhGIhpe9JaMDv-wSqDU8Qw'
    
    print("Test 1: Normal API Key initialization")
    try:
        client1 = genai.Client(api_key=token)
        # Attempt minimal call
        list(client1.models.list())
        print("Test 1 success!")
    except Exception as e:
        print("Test 1 Failed:")
        traceback.print_exc()

    print("\nTest 2: Vertex AI initialization with API key")
    try:
        client2 = genai.Client(vertexai=True, project='antigravity-innovations', location='europe-west1', api_key=token)
        list(client2.models.list())
        print("Test 2 success!")
    except Exception as e:
        print("Test 2 Failed:")
        traceback.print_exc()

    print("\nTest 3: Vertex AI initialization treating AQ. as an OAuth Token")
    try:
        creds = oauth_credentials.Credentials(token)
        client3 = genai.Client(vertexai=True, project='antigravity-innovations', location='europe-west1', credentials=creds)
        list(client3.models.list())
        print("Test 3 success!")
    except Exception as e:
        print("Test 3 Failed:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
