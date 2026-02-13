#!/bin/bash
set -e

# Configuration
PROJECT_ID="antigravity-innovations"
REGION="europe-west1"
BACKEND_SERVICE_NAME="looker-mcp-agent-backend"
FRONTEND_SERVICE_NAME="looker-mcp-agent-frontend"

echo "=================================================="
echo "   Cloud Run Deployment Script"
echo "=================================================="

# Check for .env file
if [ ! -f apps/agent/.env ]; then
    echo "Error: apps/agent/.env file not found!"
    exit 1
fi

# Load env vars for backend (ignoring comments)
# We safely construct the --set-env-vars argument
ENV_VARS=$(grep -v '^#' apps/agent/.env | grep -v '^$' | tr '\n' ',' | sed 's/,$//')

# 1. Deploy Backend
echo "1. Deploying Backend ($BACKEND_SERVICE_NAME)..."
# We exclude .env from upload via .dockerignore, so we inject vars here
gcloud run deploy $BACKEND_SERVICE_NAME \
  --source apps/agent \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --project $PROJECT_ID \
  --set-env-vars "$ENV_VARS"

# 2. Get Backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo "--------------------------------------------------"
echo "Backend deployed successfully!"
echo "Backend URL: $BACKEND_URL"
echo "--------------------------------------------------"

# 3. Create Dynamic Cloud Build Config for Frontend
echo "3. Building Frontend Image..."
cat > apps/web/cloudbuild_dynamic_temp.yaml <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: 
  - 'build'
  - '--build-arg'
  - 'NEXT_PUBLIC_API_URL=\${_NEXT_PUBLIC_API_URL}'
  - '-t'
  - '\${_IMAGE_NAME}'
  - '.'
images: ['\${_IMAGE_NAME}']
EOF

IMAGE_NAME="gcr.io/$PROJECT_ID/$FRONTEND_SERVICE_NAME"

# Build Frontend
gcloud builds submit apps/web \
  --config apps/web/cloudbuild_dynamic_temp.yaml \
  --project $PROJECT_ID \
  --substitutions=_NEXT_PUBLIC_API_URL=$BACKEND_URL,_IMAGE_NAME=$IMAGE_NAME

rm apps/web/cloudbuild_dynamic_temp.yaml

# 4. Deploy Frontend
echo "4. Deploying Frontend Service ($FRONTEND_SERVICE_NAME)..."
gcloud run deploy $FRONTEND_SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --project $PROJECT_ID \
  --set-env-vars NEXT_PUBLIC_API_URL=$BACKEND_URL,NEXT_PUBLIC_GOOGLE_CLIENT_ID=826056756274-7653f7jteulh4en41u5oiupqe2stur2s.apps.googleusercontent.com

# 5. Get Frontend URL
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)

echo "=================================================="
echo "Deployment Complete!"
echo "Backend URL:  $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "=================================================="
