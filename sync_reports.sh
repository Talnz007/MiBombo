#!/bin/bash
# sync_reports.sh
# Copies the latest JSON reports from the command center and pushes them to the root repository.

# Navigate to the workspace root
cd /home/talnz/PythonProjects/automatingwork || exit 1

# Create a data directory to store the synced reports in the root repo
mkdir -p data

# Copy the reports from osint-command-center (which has its own git repo) to the root data folder
cp osint-command-center/osint_latest_news.json data/osint_latest_news.json 2>/dev/null
cp osint-command-center/osint_processed_reports.json data/osint_processed_reports.json 2>/dev/null

# Git operations for the root repository
git add data/osint_latest_news.json data/osint_processed_reports.json

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "[$(date)] No new report changes to commit."
else
    git commit -m "Auto-sync: Update OSINT JSON reports [$(date +'%Y-%m-%d %H:%M:%S')]"
    
    # Push to the main branch of the root repository
    # Ensure your remote is set up, e.g., git remote add origin <URL>
    git push origin main
    echo "[$(date)] Reports successfully pushed to root repository."
fi
