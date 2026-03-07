import re

file_path = 'mcp_agent.py'
with open(file_path, 'r') as f:
    content = f.read()

# Replace the specific Claude logic that overrides the sk- key when vertex endpoint is active
original_block = """        if self.is_claude:
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

new_block = """        if self.is_claude:
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

if original_block in content:
    content = content.replace(original_block, new_block)
    print("Fixed logic successfully.")
else:
    print("Could not find the block to replace. Please manually check the file for differences.")

with open(file_path, 'w') as f:
    f.write(content)

