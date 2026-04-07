#!/bin/bash

# Configuration
PROJECT_ID="roitraining-dashboard"
# The default compute service account for this project
SERVICE_ACCOUNT="113570624021-compute@developer.gserviceaccount.com"

echo "🔐 Granting IAM permissions to service account: ${SERVICE_ACCOUNT}"

# 1. Vertex AI User (for Gemini models)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --quiet

# 2. Vertex AI Search User (for Discovery Engine Search Tool)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/discoveryengine.admin" \
    --quiet

# 3. BigQuery Roles (for querying report pipelines)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.jobUser" \
    --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.dataViewer" \
    --quiet

# 4. Firestore User (for fetching prompts from the 'sight-report' database)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/datastore.user" \
    --quiet

echo "✅ IAM permissions have been updated. Please note that propagation may take a few minutes."
