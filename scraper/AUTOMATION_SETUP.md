# Automated Schedule Update Setup

Complete guide to setting up automated, routine updates of course schedules.

## Overview

The automation system:
1. **Scrapes** NJIT course schedules periodically
2. **Updates** the catalog directory with fresh data
3. **Notifies** your API to reload the data

You can run updates:
- **Automatically** on a schedule (daily, weekly, etc.)
- **Manually** with a single command
- **Via API** from your web interface (coming soon)

## Quick Start - Manual Update

Test the updater first before setting up automation:

```bash
cd /Users/donovanmchenry/Projects/njitschedulepro/scraper

# Activate virtual environment
source venv/bin/activate

# Run a manual update
python auto_update_scheduler.py
```

This will:
1. Scrape all current course data
2. Backup your existing catalog to `courseschedules_backup_TIMESTAMP/`
3. Replace catalog with fresh data
4. Log everything to `auto_update.log`

## Automatic Scheduling Options

### Option 1: Cron Job (macOS/Linux) - Recommended

Cron runs tasks on a schedule. Perfect for daily/weekly updates.

#### Daily Update at 2 AM

```bash
# Open crontab editor
crontab -e

# Add this line (update the path to match your setup):
0 2 * * * cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && source venv/bin/activate && python auto_update_scheduler.py --headless >> auto_update.log 2>&1
```

#### Weekly Update (Sunday at 3 AM)

```bash
# Add this line to crontab:
0 3 * * 0 cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && source venv/bin/activate && python auto_update_scheduler.py --headless >> auto_update.log 2>&1
```

#### Twice Weekly (Monday and Thursday at 2 AM)

```bash
# Add this line to crontab:
0 2 * * 1,4 cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && source venv/bin/activate && python auto_update_scheduler.py --headless >> auto_update.log 2>&1
```

#### Cron Schedule Format

```
* * * * * command to execute
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, 0 and 7 = Sunday)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

**Examples:**
- `0 2 * * *` - Every day at 2:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 3 * * 0` - Every Sunday at 3:00 AM
- `0 1 1 * *` - First day of every month at 1:00 AM

#### View Existing Cron Jobs

```bash
crontab -l
```

#### Remove Cron Job

```bash
crontab -e
# Delete the line and save
```

### Option 2: launchd (macOS) - Alternative

For more control on macOS, use launchd instead of cron.

#### Create Launch Agent

Create a file: `~/Library/LaunchAgents/com.njit.schedule.updater.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.njit.schedule.updater</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/donovanmchenry/Projects/njitschedulepro/scraper/venv/bin/python</string>
        <string>/Users/donovanmchenry/Projects/njitschedulepro/scraper/auto_update_scheduler.py</string>
        <string>--headless</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/donovanmchenry/Projects/njitschedulepro/scraper</string>

    <key>StandardOutPath</key>
    <string>/Users/donovanmchenry/Projects/njitschedulepro/scraper/auto_update.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/donovanmchenry/Projects/njitschedulepro/scraper/auto_update_error.log</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

#### Load the Launch Agent

```bash
launchctl load ~/Library/LaunchAgents/com.njit.schedule.updater.plist
```

#### Check Status

```bash
launchctl list | grep njit
```

#### Manually Trigger

```bash
launchctl start com.njit.schedule.updater
```

#### Unload (Stop)

```bash
launchctl unload ~/Library/LaunchAgents/com.njit.schedule.updater.plist
```

### Option 3: systemd Timer (Linux)

For Linux servers using systemd.

#### Create Service File

`/etc/systemd/system/njit-schedule-updater.service`

```ini
[Unit]
Description=NJIT Schedule Updater
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/njitschedulepro/scraper
ExecStart=/path/to/scraper/venv/bin/python auto_update_scheduler.py --headless
StandardOutput=append:/path/to/scraper/auto_update.log
StandardError=append:/path/to/scraper/auto_update_error.log

[Install]
WantedBy=multi-user.target
```

#### Create Timer File

`/etc/systemd/system/njit-schedule-updater.timer`

```ini
[Unit]
Description=Run NJIT Schedule Updater Daily
Requires=njit-schedule-updater.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### Enable and Start

```bash
sudo systemctl enable njit-schedule-updater.timer
sudo systemctl start njit-schedule-updater.timer
```

#### Check Status

```bash
sudo systemctl status njit-schedule-updater.timer
sudo systemctl list-timers
```

### Option 4: GitHub Actions (Cloud)

Run updates on GitHub's servers for free!

Create `.github/workflows/update-schedules.yml`:

```yaml
name: Update Course Schedules

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd scraper
          pip install -r requirements.txt

      - name: Run updater
        run: |
          cd scraper
          python auto_update_scheduler.py --headless

      - name: Commit and push changes
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add courseschedules/
          git commit -m "Auto-update course schedules" || echo "No changes"
          git push
```

**Note**: This requires Chrome to be installed in the GitHub Actions runner. You may need additional setup steps.

## Configuration Options

### Command-Line Arguments

```bash
python auto_update_scheduler.py [OPTIONS]

Options:
  --term TERM           Term code (e.g., 202501)
  --no-backup          Don't backup existing catalog
  --visible            Run browser visibly (not headless)
  --api-url URL        API base URL (default: http://localhost:8000)
  --scrape-dir DIR     Temporary scrape directory
  --catalog-dir DIR    Catalog directory path
```

### Examples

```bash
# Update for Spring 2025
python auto_update_scheduler.py --term 202501

# Update without backing up old data
python auto_update_scheduler.py --no-backup

# Run with visible browser (for debugging)
python auto_update_scheduler.py --visible

# Custom catalog location
python auto_update_scheduler.py --catalog-dir /custom/path/courseschedules
```

## Monitoring and Logs

### Check Logs

```bash
# View recent logs
tail -f auto_update.log

# View last 50 lines
tail -50 auto_update.log

# Search for errors
grep ERROR auto_update.log
```

### Log File Location

`/Users/donovanmchenry/Projects/njitschedulepro/scraper/auto_update.log`

### What Gets Logged

- Scraping progress
- Number of files downloaded
- Backup creation
- Catalog update status
- Any errors or warnings
- Total execution time

## Reloading the API

After the catalog is updated, you need to reload your API to use the new data.

### Option 1: Auto-Reload (Development)

If running API with `--reload` flag:

```bash
cd /Users/donovanmchenry/Projects/njitschedulepro/api
uvicorn app.main:app --reload
```

The API will automatically detect file changes and reload.

### Option 2: Manual Restart

```bash
# Stop the API (Ctrl+C)
# Start it again
cd /Users/donovanmchenry/Projects/njitschedulepro/api
source venv/bin/activate  # or poetry shell
uvicorn app.main:app
```

### Option 3: Production (systemd)

If running as a service:

```bash
sudo systemctl restart njit-api
```

## Troubleshooting

### Scraper Fails

**Check logs:**
```bash
tail -100 auto_update.log
```

**Common issues:**
- Chrome not installed
- NJIT site down
- Network connectivity
- Insufficient disk space

**Solution:** Run manually with `--visible` to see what's happening:
```bash
python auto_update_scheduler.py --visible
```

### Cron Job Not Running

**Check if cron service is running:**
```bash
# macOS
sudo launchctl list | grep cron

# Linux
systemctl status cron
```

**Check cron logs:**
```bash
# macOS
tail -f /var/log/system.log | grep cron

# Linux
tail -f /var/log/syslog | grep CRON
```

**Common issues:**
- Wrong path in crontab
- Virtual environment not activated
- Permissions issues

### No Data Updated

**Verify files were downloaded:**
```bash
ls -lh /Users/donovanmchenry/Projects/njitschedulepro/scraper/data/temp_scrape/
```

**Verify catalog was updated:**
```bash
ls -lh /Users/donovanmchenry/Projects/njitschedulepro/courseschedules/
cat /Users/donovanmchenry/Projects/njitschedulepro/courseschedules/_update_metadata.txt
```

## Best Practices

1. **Test First**: Always run manually before setting up automation
2. **Monitor Initially**: Check logs for the first few automated runs
3. **Backup Strategy**: Keep backups enabled (`--no-backup` not recommended)
4. **Timing**: Run during low-traffic hours (2-4 AM)
5. **Frequency**:
   - Daily during registration periods
   - Weekly during normal semester
   - Don't update more than once per day
6. **Alerting**: Set up email notifications for failures (see cron MAILTO)

## Email Notifications (Cron)

Get emailed when cron jobs run:

```bash
# Add to top of crontab
MAILTO=your-email@example.com

# Then add your cron job
0 2 * * * cd /path/to/scraper && python auto_update_scheduler.py
```

You'll receive an email with the output after each run.

## Next Steps

Once you have automation set up:

1. Monitor the first few runs
2. Adjust timing/frequency as needed
3. Consider setting up monitoring alerts
4. Document your specific schedule for your team

## Support

If you encounter issues:
1. Check `auto_update.log` for errors
2. Run manually with `--visible` flag
3. Verify all paths in cron/systemd configs
4. Ensure Chrome and dependencies are installed

Happy automating! 🤖
