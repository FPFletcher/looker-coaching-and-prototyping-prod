import re

file_path = 'mcp_agent.py'
with open(file_path, 'r') as f:
    content = f.read()

# Make absolutely sure that when is_claude is False AND the key starts with AIza, is_vertex is set to False, no matter what.
# The previous change may not have fully bypassed the subsequent self.is_vertex = True line.

updated_logic = """            try:
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

if updated_logic in content:
    print("Found logic. Let's make sure it's correct.")
else:
    print("Logic was not matched. Let's force replace.")
