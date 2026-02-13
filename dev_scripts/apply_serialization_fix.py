
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

# The new Serialization Fix method
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
        Final Stability Version: Fixes 'TextContent not serializable', 
        'tool_code' hallucinations, and prompt context loss.
        """
        
        # 1. Compact Tool Definitions
        tools_desc = ""
        for tool in tools:
            tools_desc += f"- {tool['name']}: {tool['description']}. Schema: {json.dumps(tool['inputSchema'])}\n"
        
        # 2. Strict Instructions
        system_instruction = (
            "You are a Looker expert. You have access to these tools:\n"
            f"{tools_desc}\n"
            "INSTRUCTIONS:\n"
            "To call a tool, you MUST output a raw JSON object like this:\n"
            '{"tool": "tool_name", "arguments": {"arg": "val"}}\n'
            "Do NOT write Python code. Do NOT use markdown code blocks. ONLY RAW JSON.\n"
            "If you have enough information to answer the user, answer normally.\n"
            f"\nLOOKER CONTEXT:\n{explore_context}"
        )

        contents = []
        for msg in history:
            contents.append({
                "role": msg["role"] == "assistant" and "model" or "user",
                "parts": [{"text": msg["content"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": f"{system_instruction}\n\nUSER REQUEST: {user_message}"}]
        })
        
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response = self.model.generate_content(contents, safety_settings=safety)
            
            raw_text = ""
            if response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text
            
            if not raw_text:
                return {"success": False, "response": "Empty response from model.", "tool_calls": []}

            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            tool_calls = []
            final_text = ""

            if "{" in clean_text and "}" in clean_text:
                try:
                    start = clean_text.find("{")
                    end = clean_text.rfind("}") + 1
                    data = json.loads(clean_text[start:end])
                    
                    t_name = data.get("tool") or data.get("name")
                    t_args = data.get("arguments") or data.get("args") or {}
                    
                    if t_name:
                        # --- FIX START: ROBUST SERIALIZATION ---
                        raw_result = await self.execute_tool(t_name, t_args, looker_url, client_id, client_secret)
                        
                        # We MUST clean the result of TextContent objects before summarizing
                        # We convert the entire result into a safe string representation
                        safe_result = str(raw_result)
                        if isinstance(raw_result, dict) and "result" in raw_result:
                            # If it's a list of TextContent objects, extract the text
                            if isinstance(raw_result["result"], list):
                                extracted_text = []
                                for item in raw_result["result"]:
                                    if hasattr(item, 'text'):
                                        extracted_text.append(item.text)
                                    else:
                                        extracted_text.append(str(item))
                                safe_result = "\n".join(extracted_text)
                            else:
                                safe_result = str(raw_result["result"])
                        
                        tool_calls.append({"tool": t_name, "arguments": t_args, "result": safe_result})
                        # --- FIX END ---
                except Exception as e:
                    logger.warning(f"Failed to parse or execute tool: {e}")
                    final_text = raw_text
            else:
                final_text = raw_text

            if tool_calls:
                # Use the 'safe_result' string to prevent serializable errors
                summary_prompt = f"Tool result for {tool_calls[0]['tool']}:\n{tool_calls[0]['result']}\n\nSummarize this for the user request: {user_message}"
                final_gen = self.model.generate_content(summary_prompt)
                final_text = final_gen.text

            return {
                "success": True,
                "response": final_text or raw_text,
                "tool_calls": tool_calls
            }

        except Exception as e:
            logger.error(f"Gemini critical failure: {e}")
            return {"success": False, "response": f"System error: {str(e)}", "tool_calls": []}

'''

# Add spacing
new_method = new_method + "\n\n\n"

# Replace
print("Updates _process_with_gemini method for Serialization Fix...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
