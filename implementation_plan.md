# Implementation Plan: Skills Reorganization and Expansion

## Objective
We will restructure the project's skills repository, add newly gleaned insights regarding Cloud Run deployment, incorporate two new LookML skills (Top N and Period-over-Period), ensure system integrity, and perform a full redeployment.

## Steps

### 1. Structure the Skill Repositories
- Merge the newly cloned `lookml_skills` repository into our main `.agent/skills` folder. 
- Move our existing skills (`gemini_integration`, `looker_best_practices`, `responsive_design_and_renaming`) logically alongside the newly structured LookML folders. For instance, Looker Best Practices will be adapted into the root of LookML skills, and app specific skills will be categorized logically.
- Clean up the temporary `.agent/lookml_skills` clone to reduce noise.

### 2. Document the Cloud Run Deployment Fix
- Create a new skill documentation (e.g., `deployment_troubleshooting/SKILL.md`).
- Explicitly document the "One Freaking Day" learning: "Ensure the frontend's build-time environment variables (like `NEXT_PUBLIC_API_URL`) correctly point to the ACTIVE backend service. A mismatch causes the frontend to communicate with an obsolete or non-existent backend, leading to issues like 'Invalid JWT Signature' (503 Timeout) even if the backend code is technically fixed."

### 3. Add "Dynamic Top N" Skill
- Translate the provided LookML code for the "Top N of X metrics for X criteria" into a markdown skill file (`dynamic_top_n/SKILL.md`).
- Implement the derived table logic, the dynamic parameters (`ranking_metric`, `ranking_criteria`, `ranking_limit`), and the ranking dimensions/measures.

### 4. Add "Period over Period (PoP)" Skill
- Translate the LookML text from the provided images into the Period over Period skill (`period_over_period/SKILL.md`). 
- Include the parameters (`filter_quantity_or_revenue`, `comparison_range`, `comparison_type`), the dynamic markers (`pop_comparison_marker`), and the custom conditional metrics.

### 5. Run Tests
- Perform a quick check via `pytest` to make sure none of the repo reorganization broke any testing paths.

### 6. Redeploy Environment
- Deploy locally using Python / Next.js dev servers or docker (based on local running commands).
- Push the clean, fixed environments to Cloud Run using `deploy_cloud_run.sh`.
