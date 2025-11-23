#!/bin/bash
# Automated script to commit and push schedule updates
# This runs after the scraper completes

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
LOG_FILE="$( dirname "${BASH_SOURCE[0]}" )/auto_update.log"

echo "=======================================" >> "$LOG_FILE"
echo "Starting auto-commit at $(date)" >> "$LOG_FILE"
echo "=======================================" >> "$LOG_FILE"

cd "$REPO_DIR" || exit 1

# Check if there are changes in courseschedules directory
if git diff --quiet courseschedules/ && git diff --cached --quiet courseschedules/; then
    echo "No changes to commit" >> "$LOG_FILE"
    exit 0
fi

# Stage all changes in courseschedules
git add courseschedules/ >> "$LOG_FILE" 2>&1

# Create commit with timestamp
COMMIT_MSG="Auto-update course schedules - $(date '+%Y-%m-%d %H:%M')"
git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1

# Push to origin
if git push origin main >> "$LOG_FILE" 2>&1; then
    echo "✓ Successfully pushed updates to GitHub" >> "$LOG_FILE"
    echo "✓ Vercel and Render will auto-deploy" >> "$LOG_FILE"
else
    echo "✗ Failed to push to GitHub" >> "$LOG_FILE"
    exit 1
fi

echo "=======================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
