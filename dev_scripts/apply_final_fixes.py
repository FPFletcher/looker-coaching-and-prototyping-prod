
import os

file_path = "/home/admin_ffrancois_altostrat_com/Desktop/Antigravity projects/apps/agent/mcp_agent.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Update _execute_get_models_enhanced
print("Updating _execute_get_models_enhanced...")
start_marker = '    def _execute_get_models_enhanced(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:'
end_marker = '    def _execute_health_pulse(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:' # This might be further down, let's find the method end more robustly if possible, or use a known next method.
# Actually, based on previous reads, _execute_get_models_enhanced was near the end or middle? 
# Let's use the provided code completely replacing the existing one.
# We need to find where the current method is.
# If it doesn't exist (it was added in a previous step? yes "Optimize get_models"), we need to find it.

# Let's search for the definition
idx = content.find(start_marker)
if idx != -1:
    # Find the next method definition to know where to stop
    # In python, methods start with '    def ' or '    async def '
    # We can search for the next one after the start_marker
    next_method_idx = -1
    search_start = idx + len(start_marker)
    import re
    # Find next method at same indentation level
    match = re.search(r'\n    (async )?def ', content[search_start:])
    if match:
        next_method_idx = search_start + match.start()
    
    if next_method_idx != -1:
         old_method = content[idx:next_method_idx]
         new_method = r'''    def _execute_get_models_enhanced(self, url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Enhanced get_models that summarizes large lists for Gemini only."""
        try:
            logger.info(f"🔧 [GET_MODELS_ENHANCED] Listing models")
            sdk = self._init_sdk(url, client_id, client_secret)
            try:
                session = sdk.session()
                workspace = session.workspace_id
            except:
                workspace = "unknown"
            models = sdk.all_lookml_models(fields="name,project_name,explores(name)")
            formatted = []
            for m in models:
                explores = [e.name for e in (m.explores or [])]
                if not self.is_claude and len(explores) > 20:
                    explores_summary = f"{len(explores)} explores (use get_explores to list)"
                else:
                    explores_summary = explores
                formatted.append({"name": m.name, "project_name": m.project_name, "explores": explores_summary})
            if not self.is_claude and len(formatted) > 30:
                summary_models = formatted[:30]
                summary_models.append({"message": f"... and {len(formatted) - 30} more models."})
                return {"success": True, "workspace": workspace, "models": summary_models, "note": "Truncated for Gemini safety."}
            return {"success": True, "workspace": workspace, "models": formatted}
        except Exception as e:
            return {"success": False, "error": str(e)}

'''
         content = content[:idx] + new_method + content[next_method_idx:]
    else:
        print("Could not find end of _execute_get_models_enhanced")
else:
    print("Could not find _execute_get_models_enhanced")


# 2. Update _process_with_gemini
print("Updating _process_with_gemini...")
# We know this one exists and we used it before
start_marker = '    async def _process_with_gemini('
# It ends before _execute_health_pulse usually, or we can use the same regex trick
idx = content.find(start_marker)
if idx != -1:
    search_start = idx + len(start_marker)
    match = re.search(r'\n    (async )?def ', content[search_start:])
    if match:
        next_method_idx = search_start + match.start()
        
        new_method = r'''    async def _process_with_gemini(self, user_message: str, history: List[Dict[str, str]], tools: List[Dict[str, Any]], looker_url: str, client_id: str, client_secret: str, explore_context: str = "") -> Dict[str, Any]:
        """Action-First stability version: Forces tool use and fixes TextContent errors."""
        tools_desc = ""
        for tool in tools:
            tools_desc += f"- {tool['name']}: {tool['description']}. Schema: {json.dumps(tool['inputSchema'])}\n"
        
        system_instruction = (
            f"CONTEXT:\n{explore_context}\n\n"
            "You are a Looker expert. ### MANDATORY PROTOCOL:\n"
            "1. ALWAYS call 'get_dimensions' or 'get_explore_fields' FIRST to verify fields.\n"
            "2. Output a raw JSON object to call a tool: {\"tool\": \"name\", \"arguments\": {...}}\n"
            "3. DO NOT give a text answer until you have analyzed tool results.\n"
            "4. NO Python code, NO markdown blocks. ONLY RAW JSON."
        )

        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in history]
        contents.append({"role": "user", "parts": [{"text": f"{system_instruction}\n\nUSER REQUEST: {user_message}"}]})
        
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety = {cat: HarmBlockThreshold.BLOCK_NONE for cat in [HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmCategory.HARM_CATEGORY_HARASSMENT, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT]}
            response = self.model.generate_content(contents, safety_settings=safety)
            raw_text = response.text if (response.candidates and response.candidates[0].content.parts) else ""
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            tool_calls = []

            if "{" in clean_text and "}" in clean_text:
                start, end = clean_text.find("{"), clean_text.rfind("}") + 1
                data = json.loads(clean_text[start:end])
                t_name = data.get("tool") or data.get("name")
                if t_name:
                    raw_result = await self.execute_tool(t_name, data.get("arguments", {}), looker_url, client_id, client_secret)
                    # SERIALIZATION FIX: Extract text from TextContent objects
                    if isinstance(raw_result, dict) and "result" in raw_result:
                        res = raw_result["result"]
                        safe_result = "\n".join([i.text if hasattr(i, 'text') else str(i) for i in res]) if isinstance(res, list) else str(res)
                    else:
                        safe_result = str(raw_result)
                    tool_calls.append({"tool": t_name, "arguments": data.get("arguments", {}), "result": safe_result})

            if tool_calls:
                summary_prompt = f"CONTEXT: {explore_context}\nREQUEST: {user_message}\nRESULT: {tool_calls[0]['result']}\n\nAnswer using this data."
                final_text = self.model.generate_content(summary_prompt).text
                return {"success": True, "response": final_text, "tool_calls": tool_calls}
            return {"success": True, "response": raw_text, "tool_calls": []}
        except Exception as e:
            return {"success": False, "response": f"Error: {str(e)}", "tool_calls": []}

'''
        content = content[:idx] + new_method + content[next_method_idx:]
    else:
        print("Could not find end of _process_with_gemini")
else:
    print("Could not find _process_with_gemini")


# 3. Update process_message (Pipe Context)
print("Updating process_message...")
# We search for the specific block to replace
target_block = r'''        if not self.is_claude:
            try:
                result = await self._process_with_gemini(
                    user_message, history, available_tools,
                    looker_url, client_id, client_secret,
                    explore_context=explore_context
                )
'''
# The existing code typically looks like:
#         if not self.is_claude:
#             try:
#                 result = await self._process_with_gemini(
#                     user_message, history, available_tools,
#                     looker_url, client_id, client_secret,
#                     explore_context=explore_context
#                 )
# But we might have spacing differences. Let's look for the start.
start_marker = '        if not self.is_claude:'
idx = content.find(start_marker)

if idx != -1:
    # We want to replace the call.
    # Let's search for the end of the try block call which ends with )
    # This acts as a confirmation we are in the right place.
    # The user request wants to ensure explore_context is passed.
    # "Pipe Context (Update process_message): Update the if not self.is_claude: block to pass explore_context."
    # Wait, in the very first turn of this session (Step 366 context), I ALREADY updated process_message to pass explore_context.
    # "The process_message method was updated to pass the explore_context argument when calling _process_with_gemini."
    # Let's verify if I need to change it again.
    # The requested code:
    #         if not self.is_claude:
    #             try:
    #                 result = await self._process_with_gemini(
    #                     user_message, history, available_tools,
    #                     looker_url, client_id, client_secret,
    #                     explore_context=explore_context
    #                 )
    #                 yield {"type": "text", "content": result["response"]}
    #                 yield {"type": "done"}
    #             except Exception as e:
    #                 yield {"type": "error", "content": str(e)}
    #             return
    
    # Let's just blindly replace the block to be safe and ensure exact match with the "Final" request.
    # I'll use regex to match the block until `return` statement.
    match = re.search(r'        if not self.is_claude:(.*?)            return', content[idx:], re.DOTALL)
    if match:
        old_block = match.group(0)
        new_block = r'''        if not self.is_claude:
            try:
                result = await self._process_with_gemini(
                    user_message, history, available_tools,
                    looker_url, client_id, client_secret,
                    explore_context=explore_context
                )
                yield {"type": "text", "content": result["response"]}
                yield {"type": "done"}
            except Exception as e:
                yield {"type": "error", "content": str(e)}
            return'''
        content = content.replace(old_block, new_block)
    else:
        print("Could not find the process_message block to replace")

else:
    print("Could not find 'if not self.is_claude:' in process_message")


with open(file_path, "w") as f:
    f.write(content)

print(f"Successfully updated {file_path}")
