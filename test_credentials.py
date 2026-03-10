from google import genai
from google.oauth2.credentials import Credentials

access_token = "AQ.Ab8RN6IApYrJpLv1jipHJww-hpKCffNayNpfpe7tP66DJjT15w"
creds = Credentials(token=access_token)

try:
    client = genai.Client(vertexai=True, project="antigravity-innovations", location="europe-west1", credentials=creds)
    print("Created client with access token.")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='say "bound token works"'
    )
    print("Success:", response.text)
except Exception as e:
    print("Failed:", str(e))
