#!/bin/bash
set -e

# Configuration
PROJECT_ID="antigravity-innovations"
REGION="us-central1"
REPO_NAME="antigravity-repo"
BACKEND_SERVICE="antigravity-backend"
FRONTEND_SERVICE="antigravity-frontend"

echo "🚀 Starting deployment to Google Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# 1. Enable APIs
echo "🔌 Enabling required APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project "$PROJECT_ID"

# 2. Create Artifact Registry (if not exists)
echo "📦 Checking Artifact Registry..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --project "$PROJECT_ID" --location "$REGION" &>/dev/null; then
    echo "Creating repository $REPO_NAME..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Antigravity Docker Repository" \
        --project "$PROJECT_ID"
else
    echo "Repository $REPO_NAME exists."
fi

# 3. Deploy Backend
echo "🐍 Building BACKEND..."
if [ -f apps/agent/.env ]; then
    echo "Loading .env variables..."
    ENV_VARS=$(grep -v '^#' apps/agent/.env | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
else
    echo "⚠️ apps/agent/.env not found! Backend deployment might fail."
    exit 1
fi

# Create backend cloudbuild config
cat > cloudbuild.backend.yaml <<EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$BACKEND_SERVICE', '-f', 'apps/agent/Dockerfile', '.']
images:
  - '$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$BACKEND_SERVICE'
EOF

gcloud builds submit . --config cloudbuild.backend.yaml \
    --project "$PROJECT_ID"

echo "🦄 Deploying BACKEND to Cloud Run..."
gcloud run deploy "$BACKEND_SERVICE" \
    --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$BACKEND_SERVICE" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars "$ENV_VARS"

# Get Backend URL
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# 4. Deploy Frontend
echo "⚛️ Building FRONTEND..."

# Create frontend cloudbuild config
cat > cloudbuild.frontend.yaml <<EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$FRONTEND_SERVICE', '-f', 'apps/web/Dockerfile', '--build-arg', 'NEXT_PUBLIC_API_URL=$BACKEND_URL', '.']
images:
  - '$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$FRONTEND_SERVICE'
EOF

gcloud builds submit . --config cloudbuild.frontend.yaml \
    --project "$PROJECT_ID"

echo "🦄 Deploying FRONTEND to Cloud Run..."
# We pass NEXT_PUBLIC_API_URL as env var. 
# Next.js in 'standalone' mode or runtime usually respects process.env
gcloud run deploy "$FRONTEND_SERVICE" \
    --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$FRONTEND_SERVICE" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars NEXT_PUBLIC_API_URL="$BACKEND_URL"

# Get Frontend URL
FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --platform managed --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')

echo "--------------------------------------------------"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "--------------------------------------------------"
echo "🌍 Frontend URL: $FRONTEND_URL"
echo "🔌 Backend URL:  $BACKEND_URL"
echo "--------------------------------------------------"
