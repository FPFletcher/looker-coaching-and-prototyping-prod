---
description: Gemini Integration Troubleshooting & Workarounds
---

# Gemini Integration Best Practices

## Core Challenges with Gemini Models
When integrating Gemini (specifically 2.x and 3.x series) into the MCP agent loop, several native erratic behaviors were observed compared to Claude models:
1. **Premature Answering**: Gemini tends to answer the user immediately before fully analyzing the prompt or calling required tools.
2. **Schema Hallucination**: Native `google-genai` tool calling often misinterprets complex JSON schemas (like those used for LookML nested objects).
3. **TaskGroup Crashes**: Passing malformed schemas to native binary tools causes uncontrollable TaskGroup shutdown crashes.

## The JSON Output Protocol (Mandatory Workaround)
To make Gemini function identically and reliably to Claude, **DO NOT rely on Gemini's native function calling mechanics**. Instead, force the model to output a strict JSON payload. 

Include this exact block at the bottom of the System Prompt for Gemini:

```text
### REQUIRED TOOLS:
[Stringified JSON array of tools]

### MANDATORY OUTPUT PROTOCOL:
1. Output exactly ONE raw JSON object to call a tool: {"tool": "name", "arguments": {...}}
2. DO NOT give a text answer until you have analyzed tool results. Wait for the end of the prompt before answering.
3. NO Python code, NO markdown blocks. ONLY RAW JSON.
4. NEVER output text and a JSON block together in the first turn.
```

## Bridging JSON to Streaming Generators
The frontend expects an `AsyncGenerator` streaming events (`tool_use`, `tool_result`, `text`). To fulfill this while using the JSON protocol:
1. Make a synchronous `generate_content` request.
2. Parse the text for the JSON `{"tool": "..."}`.
3. `yield` the `tool_use` event.
4. Execute the tool and `yield` the `tool_result` event.
5. Make a second `generate_content_stream` request with the tool result appended to the prompt, and `yield` the text chunks.
