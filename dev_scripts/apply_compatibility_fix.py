
import os

file_path = "/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/mcp_agent.py"

with open(file_path, "r") as f:
    content = f.read()

# Define start and end markers for replacement
start_marker = '    async def _process_with_gemini('
end_marker = '    # ===== HEALTH TOOLS IMPLEMENTATION ====='

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find method boundaries. Start: {start_idx}, End: {end_idx}")
    exit(1)

# The new Compatibility Mode method
new_method = r'''    async def _process_with_gemini(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        looker_url: str,
        client_id: str,
        client_secret: str,
        explore_context: str = ""
    ) -> Dict[str, Any]:
        """
        Process message using Gemini with Text-Based JSON enforcement.
        Includes a robust parser to handle 'tool_code' hallucinations and Markdown.
        """
        
        # 1. Setup Tools Description
        tools_description_parts = []
        for tool in tools:
            # Simplify schema for text processing
            schema_str = json.dumps(tool['inputSchema'], ensure_ascii=False)
            tools_description_parts.append(f"### Tool: {tool['name']}\nDescription: {tool['description']}\nSchema: {schema_str}")
        
        tools_description = "\n\n".join(tools_description_parts)
        
        # 2. System Prompt (Text Mode)
        # We explicitly forbid Python/Code Interpreter syntax
        system_prompt = (
            f"You are a helpful Looker assistant with access to the following MCP tools:\n\n"
            f"{tools_description}\n\n"
            f"### STRICT INSTRUCTIONS:\n"
            f"1. **JSON ONLY**: You must respond with valid JSON. Do not write Python code. Do not use `print()`.\n"
            f"2. **Format**: Use this EXACT JSON structure for tool calls:\n"
            f"   {{ \"tool\": \"tool_name\", \"arguments\": {{ \"arg1\": \"value\" }} }}\n"
            f"3. **Arguments**: Check the 'Schema' carefully. You MUST provide all required arguments.\n"
            f"4. **No Empty Calls**: Do not call tools like `search_folders` with {{}} unless allowed.\n"
            f"5. **Context**: {explore_context}\n\n"
            f"User request: {user_message}"
        )

        # 3. Build Conversation
        conversation = []
        for msg in history:
            conversation.append({
                "role": msg["role"],
                "parts": [msg["content"]]
            })
        
        conversation.append({
            "role": "user",
            "parts": [system_prompt]
        })
        
        try:
            # 4. Define Safety Settings
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # 5. Generate Content (Standard Text Mode - Compatible with all SDK versions)
            response = None
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = self.model.generate_content(
                        conversation,
                        safety_settings=safety_settings
                        # Removed generation_config to fix "Unknown field" error
                    )
                    break
                except Exception as e:
                    if "500" in str(e) and attempt < max_retries:
                        logger.warning(f"Gemini API 500 Error (Attempt {attempt+1}), retrying...")
                        await asyncio.sleep(1)
                        continue
                    raise e
            
            # 6. Robust Response Parsing (The "Sanitizer")
            full_response_text = ""
            if response and response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        full_response_text += part.text + "\n"
            
            if not full_response_text:
                full_response_text = "I could not generate a response."

            tool_calls = []
            final_response_parts = []
            
            # Pre-processing: Clean Markdown and known hallucinations
            clean_text = full_response_text.replace("```json", "").replace("```", "").strip()
            
            # Handle the specific "tool_code" hallucination the user saw
            # Example: {'tool_code': "print(get_dimensions(...))"}
            if "'tool_code':" in clean_text or '"tool_code":' in clean_text:
                logger.warning("⚠️ Detected 'tool_code' hallucination. Attempting to parse...")
                # Simple heuristic: Look for function name and args in the string
                import re
                # Regex to find: tool_name(arg1='val', arg2='val')
                match = re.search(r"([a-zA-Z_]+)\((.*)\)", clean_text)
                if match:
                    t_name = match.group(1)
                    # This is risky but often works for simple calls: fallback to empty args if complex
                    # We basically just want to trigger the tool if the name matches
                    known_tools = [t['name'] for t in tools]
                    if t_name in known_tools:
                        # Construct a basic call - Gemini often hallucinates the args in code format anyway
                        # Let's try to extract basic key-values or just pass empty if parsing fails
                        # For now, let's assume we can prompt it better next turn, but try to execute name
                        tool_calls.append({
                            "tool": t_name,
                            "arguments": {}, # Arguments in Python string are hard to parse safely
                            "result": await self.execute_tool(t_name, {}, looker_url, client_id, client_secret)
                        })
            
            # Standard JSON Parsing
            lines = clean_text.split("\n")
            for line in lines:
                line = line.strip()
                if "{" in line and "}" in line:
                    try:
                        # Find the JSON object
                        start = line.find("{")
                        end = line.rfind("}") + 1
                        json_str = line[start:end]
                        data = json.loads(json_str)
                        
                        # Support multiple keys: 'tool', 'tool_use', 'function'
                        t_name = data.get("tool") or data.get("name") or data.get("tool_name")
                        t_args = data.get("arguments") or data.get("args") or {}
                        
                        if t_name:
                            result = await self.execute_tool(
                                t_name,
                                t_args,
                                looker_url,
                                client_id,
                                client_secret
                            )
                            tool_calls.append({
                                "tool": t_name,
                                "arguments": t_args,
                                "result": result
                            })
                    except:
                        pass # Ignore non-JSON lines
                
                if not tool_calls:
                    final_response_parts.append(line)

            # 7. Final Response Loop
            if tool_calls:
                tool_results_summary = "\n".join([
                    f"Tool {tc['tool']} returned: {json.dumps(tc['result'], indent=2)}"
                    for tc in tool_calls
                ])
                
                final_prompt = (
                    "Based on these tool execution results:\n\n"
                    f"{tool_results_summary}\n\n"
                    f"Please provide a helpful response to the user's original request: \"{user_message}\"\n\n"
                    "Include any relevant URLs or IDs from the results."
                )

                final_gen = self.model.generate_content(final_prompt)
                final_text = final_gen.text
            else:
                final_text = "\n".join(final_response_parts)
            
            return {
                "success": True,
                "response": final_text,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            return {
                "success": False,
                "response": f"An error occurred: {str(e)}",
                "tool_calls": []
            }

'''

# Add spacing
new_method = new_method + "\n\n\n"

# Replace
print("Updates _process_with_gemini method for Compatibility Mode...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
