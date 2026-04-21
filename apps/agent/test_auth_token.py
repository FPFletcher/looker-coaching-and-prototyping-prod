from google import genai
import traceback

def test_key(key, name):
    print(f"\n--- Testing {name} ---")
    
    print("\n  Method A: As plain API key (AI Studio / Vertex API Key format)")
    try:
        client = genai.Client(api_key=key) # Standard API key method
        models = list(client.models.list())
        print(f"  Success (A)! Listed {len(models)} models.")
        return True
    except Exception as e:
        print(f"  FAILED A: {e}")

    print("\n  Method B: As Vertex API key with vertexai=True")
    try:
        from google.auth.credentials import AnonymousCredentials
        # sometimes Vertex takes api key differently?
        client = genai.Client(vertexai=True, location='europe-west1', project='antigravity-innovations', api_key=key)
        models = list(client.models.list())
        print(f"  Success (B)! Listed {len(models)} models.")
        return True
    except Exception as e:
        print(f"  FAILED B: {e}")

old_key_looker_core = 'AQ.Ab8RN6Jv1IUeOiEpY2dmAkD6PZeXkhGIhpe9JaMDv-wSqDU8Qw'
new_key_antigravity = 'AQ.Ab8RN6Ljoi9PCQfD3fEgEQ-wiAogIYtnLag_fMpIYVJo9XmboQ'

test_key(old_key_looker_core, "Key 1 (looker-core bound)")
test_key(new_key_antigravity, "Key 2 (antigravity bound)")
