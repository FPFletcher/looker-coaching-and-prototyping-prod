---
description: How to deploy changes - localhost first, then Cloud Run ONLY with user approval
---

# Deployment Workflow

## ⚠️ CRITICAL RULES
1. **ALWAYS test locally BEFORE Cloud Run deployment**
2. **NEVER deploy to Cloud Run without explicit user approval** — production is used by many users

## Step 1: Verify Code Logic & Syntax (Safety Checks)
// turbo-all
```bash
python3 tests/verify_frontend_logic.py && echo "✅ Frontend Logic Verified"
cd apps/agent && python3 -m py_compile mcp_agent.py && echo "✅ Backend Syntax Verified"
```

## Step 2: Start Local Backend
```bash
cd apps/agent && pip install -r ../../requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Wait for "Uvicorn running" message.

## Step 3: Start Local Frontend
```bash
cd apps/web && npm run dev
```
Wait for "Ready" message.

## Step 4: Verify Locally
Open http://localhost:3000 in the browser and test the changes.

## Step 5: ASK USER Before Cloud Run
**STOP HERE.** Tell the user:
> "✅ Changes verified locally. Ready to deploy to Cloud Run (production). Should I proceed?"

**Do NOT run `deploy_cloud_run.sh` until the user explicitly says yes.**

## Step 6: Deploy to Cloud Run (only after approval)
```bash
bash deploy_cloud_run.sh
```
Select the appropriate option (1=backend, 2=frontend, 3=both).
