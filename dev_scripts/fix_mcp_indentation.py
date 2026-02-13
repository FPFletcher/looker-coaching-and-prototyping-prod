
import os
import re

file_path = "/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/mcp_agent.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Fix process_message call if not already fixed
# We look for the specific call pattern
if 'looker_url, client_id, client_secret\n' in content and 'explore_context=explore_context' not in content:
    print("Fixing process_message call...")
    content = content.replace(
        'looker_url, client_id, client_secret\n',
        'looker_url, client_id, client_secret,\n                    explore_context=explore_context\n'
    )

# 2. Extract the _process_with_gemini method and replace it
# We'll use string finding for start and end
start_marker = '    async def _process_with_gemini('
end_marker = '    # ===== HEALTH TOOLS IMPLEMENTATION ====='

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find method boundaries. Start: {start_idx}, End: {end_idx}")
    exit(1)

# The new method content
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
        """Process message using Gemini with Manual JSON Tool calling (Safe Mode)."""
        
        # 1. Setup the Manual Schema Prompt
        tools_description_parts = []
        for tool in tools:
            schema_str = json.dumps(tool['inputSchema'], ensure_ascii=False)
            tools_description_parts.append(f"### Tool: {tool['name']}\nDescription: {tool['description']}\nSchema: {schema_str}")
        
        tools_description = "\n\n".join(tools_description_parts)
        
        system_prompt = (
            f"You are a helpful Looker assistant with access to the following MCP tools:\n\n"
            f"{tools_description}\n\n"
            f"### STRICT TOOL USE RULES:\n"
            f"1. **Argument Fidelity**: Check the 'required' list in the Schema. You MUST provide all required arguments.\n"
            f"2. **No Empty Calls**: Do not call tools like `search_folders` or `create_chart` with empty arguments `{{}}` unless the schema explicitly allows it.\n"
            f"3. **Output Format**: To call a tool, output a single line of JSON:\n"
            f"   {{'tool_call': {{'name': 'tool_name', 'arguments': {{...}}}}}}\n"
            f"4. **No Native Syntax**: Do not use XML tags or 'call:...' syntax.\n"
            f"5. **Thoughts**: You may think step-by-step before answering.\n\n"
            f"When a user asks you to do something:\n"
            f"1. Determine which tool(s) to use\n"
            f"2. Call the tool(s) with PRECISE arguments (e.g. title, model_name)\n"
            f"3. Return a helpful response based on the results"
            f"\n\n{explore_context}"
        )

        # 2. Build Conversation
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
            # 3. Define Safety Settings (Prevents the 500 Errors)
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # 4. Generate Content
            response = None
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = self.model.generate_content(
                        conversation,
                        safety_settings=safety_settings 
                    )
                    break
                except Exception as e:
                    if "500" in str(e) and attempt < max_retries:
                        logger.warning(f"Gemini API 500 Error (Attempt {attempt+1}), retrying...")
                        await asyncio.sleep(1)
                        continue
                    raise e
            
            # 5. Safe Response Parsing
            full_response_text = ""
            if response and response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        full_response_text += part.text + "\n"
            
            if not full_response_text:
                full_response_text = "I could not generate a response."

            # 6. Parse Manual Tool Calls
            tool_calls = []
            lines = full_response_text.strip().split("\n")
            final_response_parts = []
            
            for line in lines:
                line = line.strip()
                if "tool_call" in line and line.startswith("{") and line.endswith("}"):
                    try:
                        tool_call_data = json.loads(line)
                        if "tool_call" in tool_call_data:
                            tool_name = tool_call_data["tool_call"]["name"]
                            tool_args = tool_call_data["tool_call"]["arguments"]
                            
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
                    except json.JSONDecodeError:
                        final_response_parts.append(line)
                else:
                    if line:
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
                
                final_text = ""
                if final_gen.candidates:
                    for part in final_gen.candidates[0].content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_text += part.text
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

# Ensure newlines around method
new_method = new_method + "\n\n"

# Replace
print("Replacing _process_with_gemini method...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
