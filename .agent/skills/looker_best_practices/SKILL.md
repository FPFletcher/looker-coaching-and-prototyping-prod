---
name: Looker Best Practices & Protocols
description: Essential guidelines, protocols, and mandatory sequences for interacting with Looker, creating dashboards, and visualizing data.
---

# Looker Best Practices & Protocols

This skill documents critical learnings and mandatory procedures for Looker operations. You MUST follow these protocols to ensure stability, correctness, and user trust.

## 1. Automatic Query Visualization Protocol

**MANDATORY FOR ALL SINGLE QUERY/CHART REQUESTS**

When the user asks for data analysis that results in ONE query/visualization (not a dashboard):

### Step 1: Run Query
- Use `query` or `run_look` to get data.

### Step 2: Get Embed URL
- IMMEDIATELY call `query_url` with parameters IDENTICAL to the query.
- **CRITICAL:** Do NOT modify the URL returned by `query_url`. Use it exactly as provided.

### Step 3: Present Visualization
- Format as a Markdown link: `[Interactive Chart](<exact_url_from_response>)`
- **NEVER** use `<iframe>` tags.
- **NEVER** use placeholder URLs (e.g., `googledemo`, `looker-demo`).
- **NEVER** invent domain names.

### Single Query vs Dashboard Decision Tree
- Single metric/chart → Use `query` + `query_url`.
- Multiple related charts → Use `create_dashboard` sequence.
- User says "dashboard" → Use `create_dashboard` sequence.
- User says "show me", "analyze", "top 10" → Single query.

---

## 2. Mandatory Dashboard Creation Sequence

**To prevent hallucinations (claiming tiles are added when they are not), you MUST follow this sequence strictly.**

### Step 1: Create Dashboard
- Call `create_dashboard`.
- **STOP** and wait for the `dashboard_id`.
- Lock this `dashboard_id`. Do NOT proceed without it.

### Step 2: Add Elements (Tiles)
- **State:** "Adding tiles..."
- Call `add_dashboard_element` for EACH tile.
- **Requirements:**
    - `dashboard_id`: The ID from Step 1.
    - `query_def` OR `query_id`: Mandatory.
    - `type`: usually `vis`.
- ⛔ **FORBIDDEN:** Saying "Tile added" without a successful `add_dashboard_element` API call.
- ⛔ **FORBIDDEN:** Presenting the dashboard URL if `add_dashboard_element` was NOT called or failed.
- ⛔ **FORBIDDEN:** Embedding a dashboard with zero elements. ALWAYS add at least one tile first.
- ✅ **REQUIRED:** If `add_dashboard_element` fails, report the error explicitly and stop.

### Step 3: Add Filters
- Call `create_dashboard_filter`.
- **MANDATORY:** Every dashboard MUST have at least 1 filter (e.g., Date Range).

### Step 4: Final Presentation
- ONLY AFTER all elements are successfully added, present the dashboard link.
- **Verify tile count > 0 before embedding.**
- Link format: `[Interactive Dashboard](<dashboard_url>)` (ensure it uses `/embed/dashboards/`).

---

## 3. URL Integrity & Short Links

**NEVER use Looker "Short Links" (`/x/...`).**

- **Why:** They are redirects that fail in iframes due to authentication/cookie issues.
- **Solution:** Always use the full, interactive URL:
    - `https://<looker_url>/explore/<model>/<view>?qid=<client_id>&toggle=dat,pik,vis`
- The backend `query_url` tool is configured to return this format. **Do not alter it.**
- The frontend `ChatInterface` automatically converts this to `/embed/explore/...` for display.

---

## 4. Anti-Hallucination Rules (Zero Tolerance)

**Severity: CRITICAL — Violation destroys user trust.**

- ⛔ **Forbidden:** Claiming actions that did not happen (e.g., "I've added the tile" without calling the tool).
- ⛔ **Forbidden:** Assuming success without checking the tool output JSON.
- ⛔ **Forbidden:** Inventing `dashboard_id`, `query_id`, or explore names.
- ⛔ **Forbidden:** Presenting a dashboard URL after `create_dashboard` but BEFORE any `add_dashboard_element` call.
- ⛔ **Forbidden:** Using text feedback as a substitute for an API call result.
- ✅ **Required:** Verify every tool call result before proceeding.
- ✅ **Required:** If `add_dashboard_element` fails, report the error, do NOT claim success.
- ✅ **Required:** If a previous chat was stopped mid-way (user hit 'Stop'), treat that context as **INCOMPLETE**. Do NOT assume any tool from the previous turn completed successfully.

---

## 5. Technical Context & Session Isolation

- **Context Persistence:** Session context is saved per-session to `.lookml_context_{session_id}.json`. Each chat has a unique `session_id`. Do NOT assume context from another chat is available.
- **Chat Stop/Resume:** When the user resumes a stopped chat, the previous session's context file is reloaded by matching `session_id`. You will see notes in the history like `[Attempted to use tool 'X' ... but the user aborted]`. Treat these as INCOMPLETE actions. DO NOT claim they succeeded.
- **Explore Name Hallucinations:** In POC mode, the ONLY valid explore names are those registered in the current session's LookML context. Do NOT invent or guess explore names. Always derive the explore name from the `explore:` block in the model file you created, NOT from the `view_name`.
- **POC Mode:** In "POC Mode", explore context is disabled to prevent hallucinating tables from other connections. Verify tables exist using `get_connection_tables` before generating LookML.
- **POC Model Inclusions:** ALWAYS add `include: "/*.view.lkml"` to model files generated in POC mode to ensure all views are available.

---

## 6. Visual Reporting Framework

**MANDATORY FOR ALL ANALYSIS OUTPUTS**

Every analysis (dashboard or single query) must include the following 4 distinct sections:

### 1. Highlight / Insight 💡
- **What happened?** A concise summary of the key finding.
- Example: "Revenue increased by 15% WoW driven by the 'Summer Sale' campaign."

### 2. Trends / Context 📈
- **How is it changing?** Compare current data to historical performance or benchmarks.
- Use Line charts for time series.
- Use Bar charts for categorical comparison.
- Always include % change or YoY/MoM metrics.

### 3. Recommendations / Actionable Steps 🚀
- **What should we do?** Provide concrete next steps based on the data.
- Example: "Increase spend on 'Summer Sale' campaign by 20% to maximize ROI."

### 4. Follow-up Questions ❓
- **What else should we explore?** Suggest 2-3 logical next questions to deepen the analysis.

---

## 7. Visualization Quality Assurance (QA) & Q&A

**Checklist before presenting ANY chart or dashboard:**

- [ ] **Data Density:** Is the chart readable? (Limit pies to 5 slices, bars to 10-15 categories).
- [ ] **Titles:** Does the title clearly state *what* is being shown? (e.g., "Weekly Revenue by Category" vs "Revenue").
- [ ] **Axes & Labels:** Are axes labeled? Are numbers formatted (Currency, %, etc.)?
- [ ] **Color:** Are colors consistent? (e.g., 'Revenue' is always Green, 'Cost' is always Red).
- [ ] **Chart Type (CRITICAL — use ONLY valid Looker `vis_config.type` values):**
    You MUST use one of the exact strings from this table. Using anything else (e.g., `looker_single_value`) WILL cause an API error.

    | Visual Goal | Valid `vis_config.type` value |
    |---|---|
    | Single metric / KPI | `single_value` |
    | Bar chart (vertical) | `looker_bar` |
    | Column chart (horizontal) | `looker_column` |
    | Line chart | `looker_line` |
    | Area chart | `looker_area` |
    | Scatter plot | `looker_scatter` |
    | Pie chart | `looker_pie` |
    | Data table | `looker_grid` |
    | Funnel | `looker_funnel` |
    | Map (geographic) | `looker_google_map` |
    | Timeline / Gantt | `looker_timeline` |
    | Waterfall | `looker_waterfall` |
    | Boxplot | `looker_boxplot` |
    | Word cloud | `looker_wordcloud` |

    ⛔ **FORBIDDEN:** `looker_single_value` — use `single_value` instead.
    ⛔ **FORBIDDEN:** Any type string not in this table.
    ✅ **REQUIRED:** Before calling `add_dashboard_element`, verify your `vis_config.type` is in this table.

- [ ] **Zero Baseline:** DO NOT truncate y-axis for bar charts.
- [ ] **Visual Q&A (MANDATORY):** Run extensive Q&A on each visual added.
    - Does the metric actually exist in the explore?
    - Does the visual format make sense for the data scale?
    - Have you tried alternating the chart type to find the most impactful representation?

---

## 8. Clarification Mandate

**MANDATORY PROTOCOL**

If a user request is ambiguous, lacking detail, or technically contradictory:
- **STOP** immediately.
- **ALWAYS** ask back clarifying questions before proceeding with tool calls.
- Prioritize accuracy over speed.

---

## 9. Period over Period (PoP) Analysis Pattern

**MANDATORY FOR ALL "PERIOD OVER PERIOD" REQUESTS**

When a user asks for "PoP", "YoY", "MoM" or generic "period comparison" in a POC context (where you cannot rely on complex derived tables), **YOU MUST USE "Method 6: Any two arbitrary periods"**.

**Reference:** [Methods for Period Over Period (PoP) Analysis in Looker](https://discuss.google.dev/t/methods-for-period-over-period-pop-analysis-in-looker-method-6-any-two-arbitrary-periods/119273)

### The Pattern
You need **two** parameters and a dimension that filters based on them.

```lookml
# 1. parameters
parameter: current_period_filter {
  type: date
  label: "Current Period"
}

parameter: previous_period_filter {
  type: date
  label: "Previous Period"
}

# 2. dimension
dimension: period_selected {
  type: string
  sql:
    CASE
      WHEN {% condition current_period_filter %} ${created_raw} {% endcondition %} THEN 'Current Period'
      WHEN {% condition previous_period_filter %} ${created_raw} {% endcondition %} THEN 'Previous Period'
      ELSE NULL
    END ;;
}
```

### Usage
1.  **Filter** on `period_selected` is not null.
2.  **Pivot** on `period_selected`.
3.  **Measure** can be any existing measure (e.g., `count`, `total_revenue`).

---

## 9. LookML Extends Deep Dive

**When to use:** To reuse logic from existing views or explores without copying code.

### The `extends` Param
-   **Views:** `extends: [view_name]` copies all fields/parameters from `view_name` into the current view.
-   **Explores:** `extends: [explore_name]` copies all joins/fields from `explore_name` into the current explore.

### Critical Rules for Extends:
1.  **Must Include File:** You MUST `include:` the file containing the object you are extending.
    -   `include: "/views/base_view.view.lkml"`
2.  **Order Matters:** The *last* item in the list takes precedence.
    -   `extends: [view_a, view_b]` -> `view_b` overrides `view_a`.
3.  **Field Overrides:** To modify a field, redefine it with the *same name*.
    -   Only the changed parameters need to be listed (e.g., changing `label` or `sql`).

### Common Failures & Fixes:
-   **Failure:** "Could not find view/explore to extend"
    -   **Fix:** Check the `include:` path. ensure the file is actually included in the model or view file.
-   **Failure:** "Field not found"
    -   **Fix:** Ensure the base view actually has that field. Use `get_project_files` to verify.

---

## 10. LOOKML ARTIFACT NAMING PROTOCOL (PREVENTS HALLUCINATION)

**Severity: CRITICAL**
**Problem:** AI invents model/explore names instead of using actual created names.
**Impact:** `get_explore_fields_from_context` fails, dashboards break, queries fail.

### RULE 1: AUTO-REGISTRATION AWARENESS

When you call `create_project_file`, the tool AUTOMATICALLY registers artifacts in context:
- ✅ **Models** are registered by their `connection:` declaration.
- ✅ **Explores** are registered by their `explore: name {}` declaration.
- ✅ **Views** are registered by their `view: name {}` declaration.

**YOU DO NOT NEED `get_git_branch_state` TO FIND NAMES YOU JUST CREATED.**

### RULE 2: EXTRACT NAMES FROM YOUR OWN CREATIONS (MANDATORY)

**IMMEDIATELY after creating ANY LookML file, create a NAME LOCK checklist in your thought process:**

Example - After creating `cdp_model.model.lkml`:
-   **File created:** `cdp_model.model.lkml`
-   **Model name:** `cdp_model` (from: `connection: "..."`)
-   **Explore name:** `users` (from: `explore: users {`)
-   **Base view:** `users` (from: `from: users` or `explore` name if no `from:`)

**THESE ARE THE ONLY NAMES THAT EXIST. Use them in ALL subsequent calls.**

### RULE 3: EXPLORE NAME vs BASE VIEW (CRITICAL DISTINCTION)

**The #1 cause of naming errors:**

```lookml
explore: customer_analytics {
  from: users
  join: orders { ... }
}
```

-   ❌ **WRONG:** explore_name = "users" (that's the base view!)
-   ✅ **CORRECT:** explore_name = "customer_analytics" (that's the explore name!)

**ALWAYS use the name after `explore:`, NOT the name after `from:`**

### ENFORCEMENT CHECKLIST (Before ANY _from_context tool call):
1.  **Did I create this LookML file this session?**
    -   YES: Extract names from the content I wrote.
    -   NO: Call `get_models`/`get_explores` or ask user.
2.  **Can I see the exact line with the model/explore name?**
    -   YES: Copy it exactly.
    -   NO: **STOP**. I'm hallucinating.
3.  **Am I using the `explore:` name or the `from:` name?**
    -   **explore:** name ✅
    -   **from:** name ❌ WRONG

**FORBIDDEN PATTERNS:**
-   ❌ Using names like "user_360", "cdp_analytics", "customer_insights" that sound plausible but weren't created.
-   ❌ Assuming standard naming conventions without verification.
-   ❌ Calling `get_explore_fields_from_context` before establishing **NAME LOCK**.
-   ❌ Confusing base view names with explore names.

**REQUIRED PATTERNS:**
-   ✅ Create **NAME LOCK** immediately after `create_project_file`.
-   ✅ Reference your own **NAME LOCK** for all subsequent calls.
-   ✅ If unsure, re-read the file check logic.
-   ✅ State explicitly: "Using model='X', explore='Y' from NAME LOCK".
