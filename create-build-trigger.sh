#! /bin/sh
# Set your variables
export TRIGGER_NAME="deploy-on-tag-suffix"
export GITHUB_OWNER=""
export REPO_NAME=""

gcloud beta builds triggers create github \
    --name="${REPO_NAME}-deploy-on-tag-suffix" \
    --repo-owner="${GITHUB_OWNER}" \
    --repo-name="${REPO_NAME}" \
    --tag-pattern=".*-deploy$" \
    --build-config="cloudbuild.yaml" \
    --region="global"
