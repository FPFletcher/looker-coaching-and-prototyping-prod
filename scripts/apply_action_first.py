
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

# The new Action-First method
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
        Action-First Stability Version: FORCES tool usage before answering.
        Fixes TextContent errors and ensures UI context is obeyed.
        """
        
        # 1. Compact Tool Definitions
        tools_desc = ""
        for tool in tools:
            tools_desc += f"- {tool['name']}: {tool['description']}. Schema: {json.dumps(tool['inputSchema'])}\n"
        
        # 2. ACTION-FIRST System Instruction
        # We explicitly tell Gemini it MUST call a tool first.
        system_instruction = (
            f"CONTEXT:\n{explore_context}\n\n"
            "You are a Looker expert. You have access to these tools:\n"
            f"{tools_desc}\n"
            "### MANDATORY PROTOCOL:\n"
            "1. ALWAYS call 'get_dimensions' or 'get_explore_fields' FIRST to verify fields in the selected context.\n"
            "2. You MUST output a raw JSON object to call a tool. Example:\n"
            '{"tool": "get_dimensions", "arguments": {"model": "...", "explore": "..."}}\n'
            "3. DO NOT give a text answer until you have received and analyzed tool results.\n"
            "4. Do NOT write Python code. Do NOT use markdown blocks. ONLY RAW JSON."
        )

        contents = []
        # History needs to be correctly mapped for Gemini's roles
        for msg in history:
            contents.append({
                "role": "model" if msg["role"] == "assistant" else "user",
                "parts": [{"text": msg["content"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": f"{system_instruction}\n\nUSER REQUEST: {user_message}"}]
        })
        
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in [
                HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
            ]}

            # Step 1: Force the tool call
            response = self.model.generate_content(contents, safety_settings=safety)
            raw_text = response.text if (response.candidates and response.candidates[0].content.parts) else ""
            
            if not raw_text:
                return {"success": False, "response": "Model returned empty.", "tool_calls": []}

            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            tool_calls = []
            final_text = ""

            # Step 2: Extract and Execute Tool
            if "{" in clean_text and "}" in clean_text:
                try:
                    start, end = clean_text.find("{"), clean_text.rfind("}") + 1
                    data = json.loads(clean_text[start:end])
                    t_name = data.get("tool") or data.get("name")
                    t_args = data.get("arguments") or data.get("args") or {}
                    
                    if t_name:
                        # ROBUST SERIALIZATION FIX
                        raw_result = await self.execute_tool(t_name, t_args, looker_url, client_id, client_secret)
                        
                        # Extract text from TextContent objects to prevent JSON errors
                        if isinstance(raw_result, dict) and "result" in raw_result:
                            res = raw_result["result"]
                            if isinstance(res, list):
                                safe_result = "\n".join([item.text if hasattr(item, 'text') else str(item) for item in res])
                            else:
                                safe_result = str(res)
                        else:
                            safe_result = str(raw_result)
                            
                        tool_calls.append({"tool": t_name, "arguments": t_args, "result": safe_result})
                except Exception as e:
                    logger.warning(f"Tool parse failure: {e}")
                    final_text = raw_text
            else:
                final_text = raw_text

            # Step 3: Second Pass - Summarize Results
            if tool_calls:
                summary_prompt = (
                    f"CONTEXT: {explore_context}\n"
                    f"USER REQUEST: {user_message}\n"
                    f"TOOL USED: {tool_calls[0]['tool']}\n"
                    f"RESULT: {tool_calls[0]['result']}\n\n"
                    "INSTRUCTIONS: Answer the user's request using the real data from the tool result above."
                )
                final_gen = self.model.generate_content(summary_prompt)
                final_text = final_gen.text

            return {
                "success": True,
                "response": final_text or raw_text,
                "tool_calls": tool_calls
            }

        except Exception as e:
            logger.error(f"Gemini protocol failed: {e}")
            return {"success": False, "response": f"System error: {str(e)}", "tool_calls": []}

'''

# Add spacing
new_method = new_method + "\n\n\n"

# Replace
print("Updates _process_with_gemini method for Action-First Logic...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
