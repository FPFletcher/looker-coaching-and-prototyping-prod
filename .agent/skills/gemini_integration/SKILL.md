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

## Vertex AI Connection & Tool Execution Protocols
Crucial learnings for stable Vertex AI integration (Looker & Anthropic/Gemini):

1. **Looker URL Handling**:
   - **Do NOT** manually append `/api/4.0` or `/login` to the base URL when initializing the Looker SDK. The SDK appends this automatically. Doing so manually causes double-path errors (e.g., `.../api/4.0/api/4.0/login`).
   - **DO** handle ports manually for Legacy instances: If domain is `.looker.com` (and not cloud/eu), ensure `:19999` is appended.

2. **Tool Result Wrapping (CRITICAL)**:
   - Vertex AI / Anthropic API is strict about tool result formats.
   - **Refrain** from returning unwrapped lists or raw objects from tools.
   - **ALWAYS** return a dictionary with a `result` key: `{"success": True, "result": { ... data ... }}`.
   - Returning data without a `result` key (or unwrapped) can cause the agent to extract an empty string, leading to `invalid_request_error` in the subsequent turn.

3. **Message History Serialization**:
   - When constructing conversation history for Vertex AI, **DO NOT** append raw SDK objects (like `ToolUseBlock`) directly.
   - **MUST** manually serialize all Assistant content blocks into pure dictionaries (`{"type": "tool_use", ...}`) before appending to the `messages` list. This prevents serialization errors unique to the Vertex AI transport layer.

4. **Multi-Region Routing**:
   - **Preview Models** (e.g., `gemini-2.0-flash`, `gemini-experimental`) are often **US-only** (`us-central1`) during early access.
   - **Always** check independent model availability. Do not assume all models are available in the default region (e.g., `europe-west1`). Implement a router to force `us-central1` for preview models.

5. **Binary vs Python Tools**:
   - **Avoid** relying on external binaries (`mcp-toolbox`) where possible.
   - **Prefer** native Python SDK implementations for core Looker tasks (queries, metadata) to ensure portability and avoid "File not found" errors.

## Cloud Run Deployment & Authentication

When deploying Python/FastAPI backends (especially those using Google Cloud Vertex AI and Gemini) to Cloud Run, follow these critical learnings:

### 1. Authentication Strategy: Hybrid Approach
The application supports two authentication modes. It is critical to configure them correctly to avoid `500` errors.

*   **Service Account (Recommended for Production)**: 
    *   Relies on Google Cloud Application Default Credentials (ADC).
    *   **Permission Requirement**: The Service Account attached to the Cloud Run service MUST have `roles/aiplatform.user` (Vertex AI User), `roles/datastore.user` (Firestore), `roles/logging.logWriter`.
    *   **Configuration**: Do **NOT** set `GOOGLE_API_KEY` or `ANTHROPIC_API_KEY` environment variables in the Cloud Run service configuration. Use `GOOGLE_APPLICATION_CREDENTIALS` pointing to a mounted secret or baked-in key (for prototyping only).
    *   **Common Error**: `API_KEY_SERVICE_BLOCKED` often occurs if a `GOOGLE_API_KEY` environment variable exists but is invalid for the service, effectively overriding the Service Account.

*   **API Key (User Provided / Fallback)**:
    *   Allows users to bring their own keys via the Frontend UI.
    *   **Implementation**: The backend code must explicitly check for keys provided in the request payload and prioritize them over ADC if present.
    *   **Frontend**: Keys stored in browser `localStorage` are domain-specific. Redeployment to a new domain requires re-entry.

### 2. Python Dependency Management: The `google-genai` Conflict
The Google Generative AI ecosystem is transitioning. Mixing SDKs causes fatal import errors.

*   **Conflict**: The legacy `google-generativeai` package and the new `google-genai` (v1.0+) package can conflict in the `google` namespace within Docker containers, leading to `ImportError: cannot import name 'genai' from 'google'`.
*   **Solution**: 
    1.  **Remove** `google-generativeai` from `requirements.txt` if migrating to the new SDK.
    2.  **Explicitly Install** `google-genai` in the `Dockerfile` to guarantee it is present in the final image layer:
        ```dockerfile
        RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir google-genai
        ```

### 3. Data Persistence
Cloud Run containers are ephemeral and stateless.

*   **Don't Use**: Local file storage (e.g., `sqlite:///chat.db`, JSON files). These are wiped on every deployment or scale-down.
*   **Use**: Cloud-native storage.
    *   **Firestore**: Ideal for chat history and user sessions.
    *   **GCS**: Ideal for file artifacts and large blobs.

### 4. Docker & Environment
*   **Baking Secrets (Anti-Pattern)**: While convenient for prototyping, baking `sa-key.json` into the Docker image is insecure. Use Google Secret Manager and mount secrets as volumes in production.
*   **Environment Hygiene**: Explicitly `unset` sensitive variables in the Dockerfile (`ENV GOOGLE_API_KEY=""`) to prevent build-time arguments from leaking into the runtime environment by default.

### 4. Vertex AI Model Mapping
- **Critical Fix**: When using Vertex AI with Application Default Credentials (ADC) on Cloud Run, ensure that any custom model ID mapping logic (e.g., transforming UI-friendly names to Vertex Model IDs) is explicitly called in the ADC initialization block. failing to do so will result in raw UI strings being sent to Vertex, causing  errors.
- **Verification**: Check `mcp_agent.py` to ensure `self._map_to_vertex_model` (or equivalent) is invoked in the `elif _AnthropicVertex and _gcp_project:` block.
