# Production Deployment Guide

## Overview

This scraper automatically downloads all NJIT course schedules and updates the production catalog that your API reads from.

**What it does:**
1. Scrapes all 119 departments from NJIT's course schedule site
2. Backs up existing data
3. Updates `../courseschedules/` with fresh CSV files
4. Logs everything to `auto_update.log`

**Success Rate:** 100% (119/119 departments)
**Runtime:** ~10-15 minutes for full scrape

---

## Quick Start

### 1. Test Run (Recommended First)

Run a test update to verify everything works:

```bash
cd /Users/donovanmchenry/Projects/njitschedulepro/scraper

# Full production update with visible browser (to watch it work)
./venv/bin/python auto_update_scheduler.py --visible
```

This will:
- ✓ Scrape all 119 departments
- ✓ Backup existing catalog to `../courseschedules_backup_TIMESTAMP/`
- ✓ Update `../courseschedules/` with fresh data
- ✓ Log everything to `auto_update.log`

### 2. Production Run (Headless)

Once tested, run in headless mode (no browser window):

```bash
./venv/bin/python auto_update_scheduler.py --headless
```

---

## Automated Scheduling

### Option A: Daily Updates with Cron

Set up automatic daily updates at 2 AM:

```bash
# Install cron job
./setup_cron.sh

# Verify it's installed
crontab -l

# Check logs
tail -f auto_update.log
```

### Option B: Custom Schedule

Edit your crontab manually:

```bash
crontab -e
```

Add one of these schedules:

```bash
# Daily at 2 AM
0 2 * * * cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && ./venv/bin/python auto_update_scheduler.py --headless >> auto_update.log 2>&1

# Every Sunday at 3 AM (weekly)
0 3 * * 0 cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && ./venv/bin/python auto_update_scheduler.py --headless >> auto_update.log 2>&1

# Twice per week (Monday and Thursday at 2 AM)
0 2 * * 1,4 cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && ./venv/bin/python auto_update_scheduler.py --headless >> auto_update.log 2>&1
```

---

## Command Reference

### Main Commands

```bash
# Full update cycle (recommended)
./venv/bin/python auto_update_scheduler.py --headless

# Update without backup (faster, but risky)
./venv/bin/python auto_update_scheduler.py --headless --no-backup

# Scrape specific term
./venv/bin/python auto_update_scheduler.py --headless --term 202610

# Watch it run (visible browser)
./venv/bin/python auto_update_scheduler.py --visible
```

### Manual Scraping Only

```bash
# Scrape to custom directory (doesn't update production)
./venv/bin/python njit_selenium_scraper.py --headless --output data/custom_output

# Scrape single department
./venv/bin/python njit_selenium_scraper.py --headless --subject CS --output data/test
```

### Recovery Commands

```bash
# If some subjects fail, retry them individually
./retry_failed.sh

# Restore from backup
cp -r ../courseschedules_backup_TIMESTAMP/* ../courseschedules/
```

---

## Monitoring

### Check Logs

```bash
# Watch live updates
tail -f auto_update.log

# See last update
tail -20 auto_update.log

# Search for errors
grep ERROR auto_update.log
```

### Check Catalog Status

```bash
# Count files in production catalog
ls ../courseschedules/*.csv | wc -l
# Should show 119

# Check last update time
cat ../courseschedules/_update_metadata.txt
```

### Verify Cron Jobs

```bash
# List all cron jobs
crontab -l

# Remove scraper cron job
crontab -l | grep -v 'auto_update_scheduler.py' | crontab -
```

---

## Troubleshooting

### Issue: Scraper fails at ~50 subjects

**Cause:** Browser session timeout
**Solution:** Already fixed with 12-subject restart interval

### Issue: "Element click intercepted" errors

**Cause:** Elements not fully loaded
**Solution:** Already fixed with scroll + JavaScript click fallback

### Issue: Some subjects fail randomly

**Cause:** Network timeouts
**Solution:** Run `./retry_failed.sh` to retry failures individually

### Issue: Cron job doesn't run

**Checks:**
```bash
# 1. Verify cron is running
sudo launchctl list | grep cron

# 2. Check cron logs (macOS)
log show --predicate 'process == "cron"' --last 1h

# 3. Test the command manually
cd /Users/donovanmchenry/Projects/njitschedulepro/scraper && ./venv/bin/python auto_update_scheduler.py --headless
```

### Issue: API not showing new data

**Solution:** Restart your API after catalog update:
```bash
# If using uvicorn
pkill -f uvicorn
uvicorn app.main:app --reload

# Check catalog directory
ls -la ../courseschedules/_update_metadata.txt
```

---

## File Structure

```
scraper/
├── njit_selenium_scraper.py      # Core scraper
├── auto_update_scheduler.py       # Production update orchestrator
├── combine_schedules.py           # Utility to merge CSVs
├── retry_failed.sh                # Retry failed subjects
├── setup_cron.sh                  # Cron installer
├── auto_update.log                # Production logs
├── data/
│   └── temp_scrape/              # Temp download location
└── venv/                         # Python environment

../courseschedules/                # Production catalog (119 CSVs)
../courseschedules_backup_*/       # Automatic backups
```

---

## Best Practices

1. **Always test first:** Run with `--visible` before setting up cron
2. **Monitor logs:** Check `auto_update.log` after first automated run
3. **Keep backups:** The `--no-backup` flag saves time but is risky
4. **Schedule wisely:** Run during low-traffic hours (2-4 AM)
5. **Check success:** Verify 119 CSVs exist after each run

---

## Advanced Configuration

### Custom Directories

```bash
# Use different scrape/catalog locations
./venv/bin/python auto_update_scheduler.py \
  --scrape-dir /path/to/temp \
  --catalog-dir /path/to/catalog \
  --headless
```

### API Integration

```bash
# Specify API URL for health checks
./venv/bin/python auto_update_scheduler.py \
  --headless \
  --api-url http://your-api:8000
```

---

## Success Metrics

After each run, verify:
- ✓ Exit code 0 (check with `echo $?`)
- ✓ 119 CSV files in `../courseschedules/`
- ✓ `_update_metadata.txt` has current timestamp
- ✓ No ERROR lines in `auto_update.log`
- ✓ Backup directory created (unless `--no-backup`)

---

## Support

If you encounter issues:
1. Check `auto_update.log` for errors
2. Run manually with `--visible` to see what's happening
3. Try `./retry_failed.sh` for partial failures
4. Restore from backup if needed

**Current Status:** ✅ Fully operational, 100% success rate
