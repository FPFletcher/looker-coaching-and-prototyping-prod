import re

file_path = 'mcp_agent.py'
with open(file_path, 'r') as f:
    content = f.read()

# 1. First inject google credentials import if not present somewhere early
if 'from google.oauth2 import credentials as google_credentials' not in content:
    content = content.replace(
        "from anthropic import AsyncAnthropic",
        "from anthropic import AsyncAnthropic\nfrom google.oauth2 import credentials as google_credentials\nfrom google.oauth2 import service_account"
    )

# 2. Add credentials setup block right after _gcp_region_gemini setup
setup_creds_code = """
        _gcp_region_gemini = os.getenv("VERTEX_REGION_GEMINI", os.getenv("VERTEX_REGION", "europe-west1"))

        _vertex_creds = None
        _vertex_access_token = None
        if _vertex_key and _vertex_key.startswith("AQ."):
            _vertex_access_token = _vertex_key
            import google.oauth2.credentials
            _vertex_creds = google.oauth2.credentials.Credentials(_vertex_key)
        elif _vertex_key and _vertex_key.strip().startswith("{"):
            try:
                import json
                from google.oauth2 import service_account
                sa_info = json.loads(_vertex_key)
                _vertex_creds = service_account.Credentials.from_service_account_info(sa_info)
            except Exception as e:
                logger.error(f"Failed to parse service account JSON: {e}")
"""

content = content.replace(
    '        _gcp_region_gemini = os.getenv("VERTEX_REGION_GEMINI", os.getenv("VERTEX_REGION", "europe-west1"))',
    setup_creds_code
)

# 3. Update AnthropicVertex initialization
anthropic_old = """\
            elif _AnthropicVertex and _gcp_project:
                # US / Vertex region → use AnthropicVertex with ADC or API key
                logger.info(f"Claude: Vertex AI (project={_gcp_project}, region={_gcp_region_claude})")
                self.client = _AnthropicVertex(
                    project_id=_gcp_project,
                    region=_gcp_region_claude,
                    http_client=httpx.AsyncClient(
                        timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                    )
                )
                self.is_vertex = True"""

anthropic_new = """\
            elif _AnthropicVertex and _gcp_project:
                # US / Vertex region → use AnthropicVertex with ADC or API key
                logger.info(f"Claude: Vertex AI (project={_gcp_project}, region={_gcp_region_claude})")
                
                anthropic_kwargs = {
                    "project_id": _gcp_project,
                    "region": _gcp_region_claude,
                    "http_client": httpx.AsyncClient(
                        timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                    )
                }
                
                if _vertex_access_token:
                    anthropic_kwargs["access_token"] = _vertex_access_token
                elif _vertex_creds:
                    anthropic_kwargs["credentials"] = _vertex_creds
                    
                self.client = _AnthropicVertex(**anthropic_kwargs)
                self.is_vertex = True"""

if anthropic_old in content:
    content = content.replace(anthropic_old, anthropic_new)
    print("Replaced Anthropic Vertex init")
else:
    print("Could NOT find Anthropic Vertex init!")

# 4. Update Gemini GenAI initialization
gemini_old = """\
            try:
                from google import genai as google_genai
                from google.oauth2 import service_account
                import json
                
                if _vertex_key and (_vertex_key.startswith("AIza") or _vertex_key.startswith("AQ.")):
                    logger.info("Gemini: Google AI Studio with API key provided. Using standard GenAI client.")
                    self.genai_client = google_genai.Client(
                        api_key=_vertex_key,
                    )
                elif _vertex_key and _vertex_key.strip().startswith("{"):
                    logger.info("Gemini: Service Account JSON provided in settings. Initializing isolated identity.")
                    try:
                        sa_info = json.loads(_vertex_key)
                        creds = service_account.Credentials.from_service_account_info(sa_info)
                        self.genai_client = google_genai.Client(
                            vertexai=True,
                            project=sa_info.get("project_id", _gcp_project),
                            location=_gcp_region_gemini,
                            credentials=creds
                        )
                    except Exception as parse_e:
                        raise Exception(f"Invalid Service Account JSON provided: {parse_e}")
                else:
                    logger.info(f"Gemini: Vertex AI with ADC (project={_gcp_project})")
                    self.genai_client = google_genai.Client(
                        vertexai=True,
                        project=_gcp_project,
                        location=_gcp_region_gemini,
                    )"""

gemini_new = """\
            try:
                from google import genai as google_genai
                
                if _vertex_key and _vertex_key.startswith("AIza"):
                    logger.info("Gemini: Google AI Studio with API key provided. Using standard GenAI client.")
                    self.genai_client = google_genai.Client(
                        api_key=_vertex_key,
                    )
                else:
                    vertex_kwargs = {
                        "vertexai": True,
                        "project": _gcp_project,
                        "location": _gcp_region_gemini,
                    }
                    if _vertex_creds:
                        logger.info("Gemini: Passing custom credentials for Vertex")
                        vertex_kwargs["credentials"] = _vertex_creds
                    
                    logger.info(f"Gemini: Vertex AI (project={_gcp_project}) Credentials={_vertex_creds is not None}")
                    self.genai_client = google_genai.Client(**vertex_kwargs)"""

if gemini_old in content:
    content = content.replace(gemini_old, gemini_new)
    print("Replaced Gemini GenAI init")
else:
    print("Could NOT find Gemini GenAI init!")

# Gemini cleanup
content = content.replace("self.model = self.model_name", "\n                self.model = self.model_name")

with open(file_path, 'w') as f:
    f.write(content)

print(f"Successfully processed {file_path}")
