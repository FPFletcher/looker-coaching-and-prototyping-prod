#!/bin/bash

# 1. Define Variables
PROJECT_ID="antigravity-innovations"
REGION="europe-west1"
REPO="antigravity-repo-eu"
GCLOUD="/snap/google-cloud-cli/425/bin/gcloud"
BACKEND_URL="https://antigravity-backend-734857282249.europe-west1.run.app"

# 2. Helper function for errors
error_exit() {
    echo "❌ Error: $1"
    exit 1
}

echo "==============================================="
echo "   🚀 Antigravity Auto-Deployer (Europe)      "
echo "==============================================="
echo "1. Deploy Backend Only (Python/FastAPI)"
echo "2. Deploy Frontend Only (Next.js)"
echo "3. Deploy EVERYTHING"
echo "==============================================="
read -p "Select an option (1-3): " choice

# --- BACKEND SECTION ---
case $choice in
    1|3)
        echo "--------------------------------------"
        echo "📦 Building Backend..."
        $GCLOUD builds submit --config backend-build.yaml . || error_exit "Backend Build Failed"

        echo "🚀 Deploying Backend..."
        $GCLOUD run deploy antigravity-backend \
            --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/antigravity-backend \
            --region ${REGION} || error_exit "Backend Deploy Failed"
        ;;
esac

# --- FRONTEND SECTION ---
case $choice in
    2|3)
        echo "--------------------------------------"
        echo "📦 Building Frontend..."
        $GCLOUD builds submit --config web-build.yaml . || error_exit "Frontend Build Failed"

        echo "🚀 Deploying Frontend..."
        $GCLOUD run deploy antigravity-web \
            --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/antigravity-web \
            --region ${REGION} \
            --allow-unauthenticated \
            --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" || error_exit "Frontend Deploy Failed"
        ;;
esac

echo "==============================================="
echo "✅ Deployment Complete!"
echo "==============================================="
