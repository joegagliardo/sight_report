#!/bin/bash

# Configuration
PROJECT_ID="roitraining-dashboard"
DATABASE_ID="sight-report"
COLLECTION_GROUP="prompts"

echo "📑 Creating Firestore composite index for collection '${COLLECTION_GROUP}' in database '${DATABASE_ID}'..."

# Command to create the composite index for (agent_name ASC, date_entered DESC)
# Documentation: https://cloud.google.com/sdk/gcloud/reference/firestore/indexes/composite/create
gcloud firestore indexes composite create \
    --project="${PROJECT_ID}" \
    --database="${DATABASE_ID}" \
    --collection-group="${COLLECTION_GROUP}" \
    --field-config field-path=agent_name,order=ascending \
    --field-config field-path=date_entered,order=descending

if [ $? -eq 0 ]; then
    echo "✅ Index creation request submitted successfully!"
    echo "🔗 View status in console: https://console.cloud.google.com/firestore/databases/${DATABASE_ID}/indexes/composite?project=${PROJECT_ID}"
else
    echo "❌ Failed to submit index creation request."
fi
