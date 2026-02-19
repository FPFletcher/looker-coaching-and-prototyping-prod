---
description: Tool Selection & Response Transparency Protocol - prevents 3 systematic LLM failures
---

# Tool Integrity Protocol

This skill documents the three most common tool-call failures in the Antigravity Looker Agent and how they are prevented via system prompt rules.

## Failure #1: Premature `_from_context` Usage

**Symptom:** Agent calls `get_explore_fields_from_context` when no context exists in the current session → fails silently.

**Root Cause:** Agent doesn't verify whether the model/explore has been registered in session memory.

**Fix:** Before using ANY `_from_context` tool, the agent must check:
- ✅ **Use _from_context** if LookML was created this session, or the model/explore was queried earlier, or `register_lookml_manually` was called.
- ❌ **Don't use _from_context** if this is the first mention. Instead: `get_models` → `get_explore_fields` (production), or `get_project_files` → `register_lookml_manually` → then `_from_context`.

**Affected Tools:**
- `get_explore_fields_from_context`
- `create_query_from_context`
- `create_chart_from_context`

---

## Failure #2: PROJECT vs MODEL Name Confusion

**Symptom:** `get_project_files(project_id="marketing_returning_customers")` → 404 error.

**Root Cause:** Agent uses the MODEL name where the PROJECT name is required.

**Fix:** The agent must understand the Looker hierarchy:
- **PROJECT** = LookML repository (e.g., `my_analytics_project`)
- **MODEL** = A `.model.lkml` file inside a project (e.g., `marketing_returning_customers`)

When given `model: X, explore: Y`, the agent knows `model` and `explore` but NOT `project`.

**Correct Action:**
1. Call `get_models` (no project_id needed)
2. If project files are needed, ASK the user: "What's your LookML project name?"
3. Never substitute model name for project_id

**Affected Tools (require project_id):**
- `get_project_files`
- `create_project_file`
- `validate_project`

---

## Failure #3: Silent Empty Responses

**Symptom:** `get_models` returns nothing → Agent says "model doesn't exist, let me build it from scratch."

**Root Cause:** Agent doesn't report empty/null responses, assumes failure = "doesn't exist."

**Fix:** After EVERY tool call, the agent MUST state the result:
- ✅ `get_models returned 47 models`
- ⚠️ `get_models returned no data (could be API issue, permissions, or no models deployed)`
- ❌ `get_project_files failed: 404 - project 'X' not found`

Then decide next action based on what was reported.

**Forbidden Behaviors:**
- Silent tool calls without reporting results
- "I see the issue..." without showing what was seen
- Jumping to workarounds without explaining why the primary path failed

---

## Correct Workflow Example

**User:** "Show me fields from order_items explore (model: marketing_returning_customers)"

**Step 1 - Check context:**
> "First mention of this explore → No session context → Can't use _from_context tools"

**Step 2 - Try production path:**
> Calls `get_models`
> "✅ get_models returned 47 models → Searching for 'marketing_returning_customers'..."
> "✅ Found! Model has explores: order_items, users, products"
> Calls `get_explore_fields` with production model

**OR if empty:**
> "⚠️ get_models returned no data"
> "I need your LookML project name to check files. What's the project name?"

**Step 3 - Never:**
- ❌ Call `get_explore_fields_from_context` (no context exists)
- ❌ Call `get_project_files(project_id="marketing_returning_customers")` (wrong ID type)
- ❌ Silently fail and offer to "build from scratch"

---

## Implementation

These rules are enforced in the system prompt at `apps/agent/mcp_agent.py` in the `_build_system_prompt()` method, injected universally before the POC/PRODUCTION mode split so they apply in ALL modes.

**System Prompt Section:** `🛡️ TOOL INTEGRITY RULES`

**Location:** After initial greeting, before POC/PROD mode block (~line 1570)
