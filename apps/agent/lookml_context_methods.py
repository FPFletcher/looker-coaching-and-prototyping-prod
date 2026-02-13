def get_lookml_context(mcp_agent, looker_url, client_id, client_secret):
    return """You are an expert Looker developer. 
    1. Verify fields using get_dimensions.
    2. Answer clearly based on LookML metadata.
    3. If fields are missing, suggest the closest match."""
