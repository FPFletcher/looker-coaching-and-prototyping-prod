#!/bin/bash
PROJECT_ID="antigravity-innovations"
ACCESS_TOKEN=$(gcloud auth print-access-token)

MODELS=("claude-sonnet-4-6@defaultclaude" "claude-sonnet-4-5@20250929")
REGIONS=("global" "europe-west1" "us-east5" "us-central1")

for REGION in "${REGIONS[@]}"; do
  echo "---------------------------------------------------"
  echo "Testing Region: $REGION"
  if [ "$REGION" == "global" ]; then
      ENDPOINT="https://aiplatform.googleapis.com"
  else
      ENDPOINT="https://${REGION}-aiplatform.googleapis.com"
  fi

  for MODEL in "${MODELS[@]}"; do
    echo "  Checking Model: $MODEL"
    # We try to get the model resource
    # For publisher models, the path is projects/$PROJECT/locations/$REGION/publishers/anthropic/models/$MODEL
    # But usually Publisher models are accessed via prediction endpoint. 
    # Let's try GET on the model resource first.
    
    URL="$ENDPOINT/v1/projects/$PROJECT_ID/locations/$REGION/publishers/anthropic/models/$MODEL"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $ACCESS_TOKEN" "$URL")
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo "  ✅ FOUND ($HTTP_CODE)"
    elif [ "$HTTP_CODE" == "404" ]; then
        echo "  ❌ NOT FOUND (404)"
    else
        echo "  ⚠️  Error ($HTTP_CODE)"
    fi
  done
done
