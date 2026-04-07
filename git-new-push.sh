#!/bin/sh

# Check if both arguments are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: Missing arguments."
    echo "Usage: ./git-new-push.sh <github-username> <repo-name>"
    exit 1
fi

# 1. Remove old history
rm -rf .git

# 2. Re-initialize
git init
git add .
git commit -m "0.0.0"

# 3. Link to new destination using the variables
git remote add origin "https://github.com/$1/$2.git"
git branch -M main

# 4. Push
git push -u origin main



