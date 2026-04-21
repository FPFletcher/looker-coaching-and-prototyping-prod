---
name: Cloud Run Deployment Troubleshooting
description: Best practices and learnings for troubleshooting environment mismatches in Next.js + FastAPI deployments on Google Cloud Run.
---

# Cloud Run Deployment Troubleshooting

## The Ghost Backend Anti-Pattern
When managing two coupled services (like a Next.js frontend and a FastAPI backend) and iterating quickly, it's very easy to assume your frontend changes or backend fixes have propagated when they haven't.

### The "One Freaking Day" Learning
We spent an entire day tracking down an "Invalid JWT Signature" (503 Timeout) authentication error, deploying backend fixes iteratively, with zero results.

**What was actually happening:**
The frontend was hardcoded at build-time with a `NEXT_PUBLIC_API_URL` pointing to `antigravity-backend`. We were testing, logging, and deploying our fixes to a completely separate test service (`selo-backend`). Because Next.js 'bakes in' `NEXT_PUBLIC_` variables at build time, the frontend was still hitting the absolute original copy of `antigravity-backend` (which still had broken SSL configurations) regardless of how many times we refreshed the page, the user hit the login button, or we pushed code to `selo-backend`.

### Key Takeaways
1. **Always Verify Cross-Service Pointers:** When troubleshooting a frontend-to-backend error, explicitly confirm that the frontend's environment variable `NEXT_PUBLIC_API_URL` points directly to the exact Cloud Run Revision/URL you just deployed.
2. **Next.js Build-Time Envs:** Environment variables in Next.js prefixed with `NEXT_PUBLIC_` MUST be supplied during docker build (`--build-arg`). Merely supplying them during `gcloud run deploy --set-env-vars` won't change them if the `next build` phase didn't incorporate them properly unless you are using runtime variables setup explicitly.
3. **Synchronize your Deployment Scripts:** Your automation/deploy scripts MUST keep the URLs mapped. In `deploy_cloud_run.sh`, whenever `antigravity-backend` is successfully built, capture its URL and parse it specifically to `web-build.yaml` as a `--build-arg`. 
4. **Log Context Verification:** If your backend logs aren't receiving a request you know you triggered from the frontend, **stop changing backend code immediately** and inspect the Network Tab on the browser to see what URL is actually being hit.
