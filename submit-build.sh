#!/bin/bash

# Configuration
PROJECT_ID="roitraining-dashboard"
REGION="us-central1"

# Get the current Git Short SHA
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

echo "🚀 Submitting build to Google Cloud Build for project: $PROJECT_ID (Tag: $IMAGE_TAG)..."

# Trigger the build manually
gcloud builds submit \
    --config=cloudbuild.yaml \
    --project=$PROJECT_ID \
    --region=$REGION \
    --substitutions=_IMAGE_TAG=$IMAGE_TAG \
    .

echo "✅ Build submission complete. Check the Google Cloud Console for real-time logs."
