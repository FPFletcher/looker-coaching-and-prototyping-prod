import re

file_path = 'mcp_agent.py'
with open(file_path, 'r') as f:
    content = f.read()

# Fix Claude: Force usage of standard Anthropic client if _claude_key is present.
# (Currently, the conditional block tests EU, then Vertx AI ADC fallback, then direct key fallback)
# We want to use direct key if it exists, regardless of REGION
claude_logic_original = """        if self.is_claude:
            # EU region → use direct Anthropic API key (Claude not on Vertex in EU)
            if self.llm_region == "EU" and _claude_key:
                logger.info("Claude: EU region → using direct Anthropic API key")
                self.client = AsyncAnthropic(
                    api_key=_claude_key,
                    timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                )
                self.is_vertex = False
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
                self.is_vertex = True
            elif _claude_key:
                logger.info("Claude: falling back to direct Anthropic API key")
                self.client = AsyncAnthropic(
                    api_key=_claude_key,
                    timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                )
                self.is_vertex = False
            else:
                raise Exception("No Claude credentials available. Provide an Anthropic API key (EU) or configure Vertex AI (US).")"""

claude_logic_new = """        if self.is_claude:
            # Use direct Anthropic key if provided, this avoids the need for Vertex / ADC
            if _claude_key:
                logger.info("Claude: Using direct Anthropic API key")
                self.client = AsyncAnthropic(
                    api_key=_claude_key,
                    timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                )
                self.is_vertex = False
            elif _AnthropicVertex and _gcp_project:
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
                self.is_vertex = True
            else:
                raise Exception("No Claude credentials available. Provide an Anthropic API key or configure Vertex AI.")"""

# Fix Gemini: Force usage of standard genai client (via Google AI Studio endpoint) if _vertex_key starts with AIza
# Ensure it totally bypasses the Vertex blocks below!
gemini_logic_original = """            try:
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
                    self.genai_client = google_genai.Client(**vertex_kwargs)
                
                self.model = self.model_name
                self.is_vertex = True
                logger.info(f"Gemini model: {self.model}")
            except Exception as e:
                raise Exception(f"Gemini initialization failed: {e}")"""

gemini_logic_new = """            try:
                from google import genai as google_genai
                
                # Check for standard Google AI Studio api key starting with 'AIza'
                if _vertex_key and _vertex_key.startswith("AIza"):
                    logger.info("Gemini: Google AI Studio with API key provided. Using standard GenAI client.")
                    self.genai_client = google_genai.Client(
                        api_key=_vertex_key,
                    )
                    self.is_vertex = False  # DO NOT USE VERTEX
                else:
                    logger.info(f"Gemini: Using Vertex AI API client (project={_gcp_project}, location={_gcp_region_gemini})")
                    vertex_kwargs = {
                        "vertexai": True,
                        "project": _gcp_project,
                        "location": _gcp_region_gemini,
                    }
                    if _vertex_creds:
                        logger.info("Gemini: Passing custom credentials for Vertex")
                        vertex_kwargs["credentials"] = _vertex_creds
                    
                    self.genai_client = google_genai.Client(**vertex_kwargs)
                    self.is_vertex = True
                
                self.model = self.model_name
                logger.info(f"Gemini model initialized: {self.model} (is_vertex: {self.is_vertex})")
            except Exception as e:
                raise Exception(f"Gemini initialization failed: {e}")"""


if claude_logic_original in content:
    content = content.replace(claude_logic_original, claude_logic_new)
    print("Fixed Claude logic.")
else:
    # Look for the previous fix which was simpler
    claude_logic_prev = """        if self.is_claude:
            # Use Direct Anthropic Key if provided (overrides Vertex)
            if _claude_key:
                logger.info("Claude: Using direct Anthropic API key")
                self.client = AsyncAnthropic(
                    api_key=_claude_key,
                    timeout=httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
                )
                self.is_vertex = False
            elif _AnthropicVertex and _gcp_project:
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
                self.is_vertex = True
            else:
                raise Exception("No Claude credentials available. Provide an Anthropic API key or configure Vertex AI.")"""
    if claude_logic_prev in content:
        content = content.replace(claude_logic_prev, claude_logic_new)
        print("Fixed Claude logic (from the previously modified block).")
    else:
        print("Could not find any Claude block to replace. Please check.")

if gemini_logic_original in content:
    content = content.replace(gemini_logic_original, gemini_logic_new)
    print("Fixed Gemini logic.")
else:
    print("Could not find Gemini block to replace.")

with open(file_path, 'w') as f:
    f.write(content)
