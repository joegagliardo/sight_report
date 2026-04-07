#!/bin/bash

# Configuration
PROJECT_ID="roitraining-dashboard"
DATABASE_ID="sight_report"
LOCATION="us-central1"

echo "🚀 Creating Firestore database '${DATABASE_ID}' in project '${PROJECT_ID}'..."

# Command to create the Firestore database in Native mode
# Documentation: https://cloud.google.com/sdk/gcloud/reference/firestore/databases/create
gcloud firestore databases create \
    --project="${PROJECT_ID}" \
    --database="${DATABASE_ID}" \
    --location="${LOCATION}" \
    --type=firestore-native

if [ $? -eq 0 ]; then
    echo "✅ Database '${DATABASE_ID}' created successfully!"
else
    echo "❌ Failed to create database. check if it already exists or if you have the correct permissions."
fi
