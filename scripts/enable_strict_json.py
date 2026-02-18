
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

# The new Strict JSON Mode method
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
        Process message using Gemini with STRICT JSON MODE.
        This forces the model to output structured JSON, preventing Python code hallucinations.
        """
        
        # 1. Setup Tools Description
        tools_description_parts = []
        for tool in tools:
            schema_str = json.dumps(tool['inputSchema'], ensure_ascii=False)
            tools_description_parts.append(f"### Tool: {tool['name']}\nDescription: {tool['description']}\nSchema: {schema_str}")
        
        tools_description = "\n\n".join(tools_description_parts)
        
        # 2. Define the STRICT Response Schema
        # This tells Gemini: "You can ONLY output this JSON structure."
        # We allow 'tool_use' (for calling tools) OR 'text_response' (for talking to user)
        response_schema = {
            "type": "object",
            "properties": {
                "tool_use": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "object"}
                    },
                    "required": ["name", "arguments"]
                },
                "text_response": {
                    "type": "string"
                }
            }
        }

        # 3. System Prompt tailored for JSON Mode
        system_prompt = (
            f"You are a helpful Looker assistant with access to the following tools:\n\n"
            f"{tools_description}\n\n"
            f"### INSTRUCTIONS:\n"
            f"You are operating in STRICT JSON MODE. You must respond with a JSON object matching this schema:\n"
            f"{{ \"tool_use\": {{ \"name\": \"...\", \"arguments\": {{...}} }} }}  <-- Use this to call a tool.\n"
            f"OR\n"
            f"{{ \"text_response\": \"...\" }}  <-- Use this to answer the user directly.\n\n"
            f"RULES:\n"
            f"1. **Argument Fidelity**: Check the tool Schema carefully. Provide ALL required arguments.\n"
            f"2. **No Empty Calls**: Do not call `search_folders` or `create_chart` with {{}} unless the schema says so.\n"
            f"3. **No Python**: Do not write `tool_code` or `print()`. Only output the JSON object.\n"
            f"4. **Step-by-Step**: If you need to think, do it internally, but the final output MUST be the JSON object above.\n"
            f"\nCONTEXT:\n{explore_context}"
        )

        # 4. Build Conversation
        conversation = []
        for msg in history:
            conversation.append({
                "role": msg["role"],
                "parts": [msg["content"]]
            })
        
        conversation.append({
            "role": "user",
            "parts": [f"{system_prompt}\n\nUser request: {user_message}"]
        })
        
        try:
            # 5. Define Safety Settings
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # 6. Generate Content with FORCED JSON
            response = None
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = self.model.generate_content(
                        conversation,
                        safety_settings=safety_settings,
                        generation_config={
                            "response_mime_type": "application/json", # <--- THE KILL SWITCH
                            "response_schema": response_schema
                        }
                    )
                    break
                except Exception as e:
                    if "500" in str(e) and attempt < max_retries:
                        logger.warning(f"Gemini API 500 Error (Attempt {attempt+1}), retrying...")
                        await asyncio.sleep(1)
                        continue
                    raise e
            
            # 7. Parse the Strict JSON Response
            # Since we forced JSON, we can parse it directly without regex/string searching
            full_response_text = response.text if response else "{}"
            tool_calls = []
            final_text = ""

            try:
                response_data = json.loads(full_response_text)
                
                # Check if it chose to call a tool
                if "tool_use" in response_data and response_data["tool_use"]:
                    tool_info = response_data["tool_use"]
                    tool_name = tool_info.get("name")
                    tool_args = tool_info.get("arguments", {})
                    
                    if tool_name:
                        # Execute the tool
                        result = await self.execute_tool(
                            tool_name,
                            tool_args,
                            looker_url,
                            client_id,
                            client_secret
                        )
                        
                        tool_calls.append({
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": result
                        })
                
                # Check if it chose to respond with text
                if "text_response" in response_data and response_data["text_response"]:
                    final_text = response_data["text_response"]

            except json.JSONDecodeError:
                logger.error(f"Failed to parse Gemini JSON: {full_response_text}")
                final_text = "Error: Model response was not valid JSON."

            # 8. Final Response Loop (Feed tool results back)
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

                # For the final summary, we relax the constraint to allow natural text
                final_gen = self.model.generate_content(final_prompt)
                final_text = final_gen.text

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
print("Updates _process_with_gemini method for Strict JSON Mode...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
