#!/bin/bash
# Setup cron job for automated scraping
# This will run the scraper daily at 2 AM

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
SCRAPER_SCRIPT="$SCRIPT_DIR/auto_update_scheduler.py"
LOG_FILE="$SCRIPT_DIR/auto_update.log"

echo "Setting up cron job for NJIT schedule scraper..."
echo ""
echo "This will run the scraper daily at 2:00 AM"
echo "Logs will be written to: $LOG_FILE"
echo ""

# Create cron entry (scrape, then commit and push)
AUTO_COMMIT_SCRIPT="$SCRIPT_DIR/auto_commit_and_push.sh"
CRON_ENTRY="0 2 * * * cd $SCRIPT_DIR && $PYTHON_PATH $SCRAPER_SCRIPT >> $LOG_FILE 2>&1 && bash $AUTO_COMMIT_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "auto_update_scheduler.py"; then
    echo "Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "auto_update_scheduler.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✓ Cron job installed successfully!"
echo ""
echo "To verify:"
echo "  crontab -l"
echo ""
echo "To remove:"
echo "  crontab -l | grep -v 'auto_update_scheduler.py' | crontab -"
echo ""
echo "Manual run:"
echo "  cd $SCRIPT_DIR && $PYTHON_PATH $SCRAPER_SCRIPT"
