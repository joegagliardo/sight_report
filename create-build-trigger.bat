@echo off

:: 1. Set your variables
set "GITHUB_OWNER="
set "REPO_NAME="
set "TRIGGER_NAME=%REPO_NAME%-deploy-on-tag-suffix"

:: 2. Create the trigger
:: The caret (^) is used for line breaks in Windows Batch
call gcloud beta builds triggers create github ^
    --name="%TRIGGER_NAME%" ^
    --repo-owner="%GITHUB_OWNER%" ^
    --repo-name="%REPO_NAME%" ^
    --tag-pattern=".*-deploy$" ^
    --build-config="cloudbuild.yaml" ^
    --region="global"

pause