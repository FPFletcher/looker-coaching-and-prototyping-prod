
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

# The new Simplified Parser method
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
        Process message using Gemini with a Simplified, High-Reliability Parser.
        Bypasses SDK version issues and handles timeouts by reducing prompt weight.
        """
        
        # 1. Ultra-Compact Tool Definitions
        tools_desc = ""
        for tool in tools:
            tools_desc += f"- {tool['name']}: {tool['description']}. Schema: {json.dumps(tool['inputSchema'])}\n"
        
        # 2. Simplest Possible System Prompt
        # This reduces the "thinking load" to prevent 504 timeouts.
        system_instruction = (
            "You are a Looker expert. You have access to these tools:\n"
            f"{tools_desc}\n"
            "INSTRUCTIONS:\n"
            "To call a tool, you MUST output a raw JSON object like this:\n"
            '{"tool": "tool_name", "arguments": {"arg": "val"}}\n'
            "Do NOT write Python code. Do NOT use markdown code blocks. ONLY JSON.\n"
            "If you have enough information to answer the user, answer normally.\n"
            f"\nLOOKER CONTEXT:\n{explore_context}"
        )

        # 3. Build parts manually to ensure request validity
        contents = []
        for msg in history:
            contents.append({
                "role": msg["role"] == "assistant" and "model" or "user",
                "parts": [{"text": msg["content"]}]
            })
        
        # Final part includes the simplified instructions + the request
        contents.append({
            "role": "user",
            "parts": [{"text": f"{system_instruction}\n\nUSER REQUEST: {user_message}"}]
        })
        
        try:
            # 4. Global Safety Bypass (Prevents 500s/Blocks)
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # 5. Generate with minimal config for stability
            response = self.model.generate_content(
                contents,
                safety_settings=safety
            )
            
            # 6. Robust "Swiss Army Knife" Parser
            # This handles text, markdown, or tool_code hallucinations
            raw_text = ""
            if response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text
            
            if not raw_text:
                return {"success": False, "response": "Empty response from Gemini.", "tool_calls": []}

            # Clean the text for parsing
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            tool_calls = []
            final_text = ""

            # Check for JSON Tool Call
            if "{" in clean_text and "}" in clean_text:
                try:
                    # Find the outermost { }
                    start = clean_text.find("{")
                    end = clean_text.rfind("}") + 1
                    data = json.loads(clean_text[start:end])
                    
                    t_name = data.get("tool") or data.get("name")
                    t_args = data.get("arguments") or data.get("args") or {}
                    
                    if t_name:
                        result = await self.execute_tool(t_name, t_args, looker_url, client_id, client_secret)
                        tool_calls.append({"tool": t_name, "arguments": t_args, "result": result})
                except:
                    # If JSON parsing fails, treat as text answer
                    final_text = raw_text
            else:
                final_text = raw_text

            # 7. Final response generation if tools were used
            if tool_calls:
                summary_prompt = f"Tool result: {json.dumps(tool_calls[0]['result'])}\n\nSummarize this for the user: {user_message}"
                final_gen = self.model.generate_content(summary_prompt)
                final_text = final_gen.text

            return {
                "success": True,
                "response": final_text or raw_text,
                "tool_calls": tool_calls
            }

        except Exception as e:
            logger.error(f"Final Gemini Attempt Failed: {e}")
            return {"success": False, "response": f"Error: {str(e)}", "tool_calls": []}

'''

# Add spacing
new_method = new_method + "\n\n\n"

# Replace
print("Updates _process_with_gemini method for Simplified Parser...")
new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, "w") as f:
    f.write(new_content)

print(f"Successfully updated {file_path}")
