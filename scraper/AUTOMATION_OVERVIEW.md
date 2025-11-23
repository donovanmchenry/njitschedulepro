# Automation System Overview

Complete automation solution for keeping your NJIT Schedule Pro website up-to-date with the latest course data.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Automation Workflow                       │
└─────────────────────────────────────────────────────────────┘

1. TRIGGER (Choose One)
   ├─ Cron Job (Scheduled - e.g., daily at 2 AM)
   ├─ Manual Command (python auto_update_scheduler.py)
   └─ API Endpoint (POST /admin/update-catalog)
            │
            ▼
2. SCRAPE
   ├─ Opens Chrome browser (headless)
   ├─ Navigates to NJIT course schedule
   ├─ Clicks through all subjects (ACCT, CS, MATH, etc.)
   ├─ Downloads CSV for each subject
   └─ Saves to temp directory
            │
            ▼
3. UPDATE
   ├─ Backs up existing catalog
   ├─ Clears old CSVs
   ├─ Copies new CSVs to catalog directory
   └─ Creates metadata file
            │
            ▼
4. RELOAD
   ├─ API automatically reloads on startup (dev mode)
   ├─ Or call POST /admin/reload-catalog
   └─ Users see fresh data
```

## Components

### 1. Scraper (`njit_selenium_scraper.py`)

**Purpose**: Download course schedule CSVs from NJIT

**How it works**:
- Uses Selenium to control Chrome browser
- Navigates through the web interface
- Clicks subjects and downloads CSVs
- Works without login credentials (public data)

**Usage**:
```bash
python njit_selenium_scraper.py
```

**Features**:
- Headless mode (no visible browser)
- Progress logging
- Error handling with retries
- Configurable delays

### 2. Auto Updater (`auto_update_scheduler.py`)

**Purpose**: Orchestrates the full update cycle

**What it does**:
1. Runs the scraper
2. Backs up existing catalog
3. Updates catalog directory
4. Logs everything

**Usage**:
```bash
python auto_update_scheduler.py
```

**Features**:
- Automatic backups
- Comprehensive logging
- Error handling
- Metadata tracking

### 3. Admin Endpoints (`api/app/admin_endpoints.py`)

**Purpose**: Allow web-based manual triggers

**Endpoints**:
- `POST /admin/update-catalog` - Trigger scraper
- `GET /admin/update-status` - Check progress
- `POST /admin/reload-catalog` - Reload from disk

**Usage**:
```typescript
// From your frontend
await fetch('/admin/update-catalog', { method: 'POST' });
```

**Features**:
- Background execution
- Status tracking
- Instant catalog reload

## Setup Options

### Option A: Scheduled Automation (Recommended)

**Best for**: Production websites that need regular updates

**Setup Time**: 5 minutes

**Steps**:
1. Install dependencies
2. Test manual run
3. Add to crontab
4. Monitor first few runs

**Example**:
```bash
# Daily at 2 AM
crontab -e
# Add: 0 2 * * * cd /path/to/scraper && python auto_update_scheduler.py --headless
```

**See**: [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md)

### Option B: Manual Trigger via API

**Best for**: Development or infrequent updates

**Setup Time**: 10 minutes

**Steps**:
1. Add admin endpoints to API
2. Create admin panel in frontend
3. Trigger updates on demand

**Example**:
```typescript
<button onClick={triggerUpdate}>
  Update Course Catalog
</button>
```

**See**: [API_INTEGRATION.md](API_INTEGRATION.md)

### Option C: Command Line (Development)

**Best for**: Testing or one-time updates

**Setup Time**: 2 minutes

**Usage**:
```bash
python auto_update_scheduler.py
```

**See**: [QUICKSTART.md](QUICKSTART.md)

## File Structure

```
njitschedulepro/
├── scraper/
│   ├── njit_selenium_scraper.py      # Core scraper
│   ├── auto_update_scheduler.py      # Update orchestrator
│   ├── auto_update.log                # Execution logs
│   ├── data/
│   │   └── temp_scrape/               # Temporary download location
│   └── venv/                          # Python dependencies
│
├── courseschedules/                   # Catalog directory (API reads from here)
│   ├── Course_Schedule_*.csv          # Course data
│   └── _update_metadata.txt           # Last update info
│
├── courseschedules_backup_*/          # Automatic backups
│
└── api/
    └── app/
        ├── main.py                    # FastAPI app
        └── admin_endpoints.py         # Admin API routes
```

## Data Flow

### Scraping Phase
```
NJIT Website → Selenium → CSV files → data/temp_scrape/
```

### Update Phase
```
data/temp_scrape/ → Backup old → courseschedules/ → API reload
```

### User Access
```
User → Frontend → API → courseschedules/ → Fresh data ✨
```

## Frequency Recommendations

| Period | Frequency | Cron Schedule |
|--------|-----------|---------------|
| **Registration Week** | Daily at 2 AM | `0 2 * * *` |
| **Mid-Semester** | Weekly (Sunday 3 AM) | `0 3 * * 0` |
| **Summer** | Bi-weekly | `0 2 1,15 * *` |
| **Off-Season** | Monthly | `0 2 1 * *` |

## Monitoring

### Check Logs

```bash
# View recent activity
tail -50 scraper/auto_update.log

# Follow live updates
tail -f scraper/auto_update.log

# Search for errors
grep ERROR scraper/auto_update.log
```

### Verify Updates

```bash
# Check catalog directory
ls -lh courseschedules/

# View last update time
cat courseschedules/_update_metadata.txt

# Count offerings
wc -l courseschedules/*.csv
```

### API Status

```bash
# Check catalog size
curl http://localhost:8000/ | jq .catalog_size

# Get update status
curl http://localhost:8000/admin/update-status
```

## Typical Update Timeline

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| **Startup** | 10s | Browser launches, page loads |
| **Scraping** | 3-5 min | Clicking subjects, downloading CSVs |
| **Processing** | 10s | Backing up, copying files |
| **Total** | ~5 min | Complete update cycle |

**Note**: First run may take longer while ChromeDriver downloads.

## Resource Usage

- **Disk Space**: ~50 MB per term (all subjects)
- **Network**: ~10 MB download per update
- **CPU**: Low (browser automation)
- **RAM**: ~500 MB (Chrome headless)

## Error Recovery

The system handles common errors automatically:

| Error | Auto-Recovery | Action Needed |
|-------|---------------|---------------|
| Network timeout | Retries 3x | None, check logs |
| Page load failure | Waits and retries | None |
| Chrome crash | Logged, exits | Check ChromeDriver |
| Disk full | Aborts, logged | Free up space |
| NJIT site down | Logged, exits | Try again later |

## Best Practices

1. **Test First**: Always run manually before automating
2. **Monitor Initially**: Check logs for first 3-5 scheduled runs
3. **Keep Backups**: Don't disable backup feature
4. **Log Rotation**: Archive old logs periodically
5. **Off-Peak Hours**: Schedule for 2-4 AM
6. **Rate Limiting**: Don't run more than once per day
7. **Alerting**: Set up email notifications (cron MAILTO)

## Security

### Protecting Admin Endpoints

Add authentication to admin endpoints:

```python
# In admin_endpoints.py
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

async def verify_admin(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(403, "Unauthorized")
```

### Environment Variables

```bash
# .env
ADMIN_API_KEY=your-secret-key-here
```

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Cron not running | Check `crontab -l`, verify paths |
| No CSVs downloaded | Run with `--visible` to debug |
| API not updating | Call `/admin/reload-catalog` |
| Chrome errors | Update Chrome, reinstall ChromeDriver |
| Permission denied | Check file permissions, user ownership |
| Timeout errors | Increase timeout in script |

## Getting Help

1. **Check logs**: `scraper/auto_update.log`
2. **Run visibly**: `python auto_update_scheduler.py --visible`
3. **Test scraper**: `python njit_selenium_scraper.py --subject CS`
4. **Verify paths**: Check all paths in cron/config files
5. **Review docs**: See detailed guides below

## Documentation Index

| Guide | Purpose | Audience |
|-------|---------|----------|
| [QUICKSTART.md](QUICKSTART.md) | Get started fast | Everyone |
| [README.md](README.md) | Main documentation | Developers |
| [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md) | Scheduling & cron | DevOps |
| [API_INTEGRATION.md](API_INTEGRATION.md) | API endpoints | Backend devs |
| [AUTOMATION_OVERVIEW.md](AUTOMATION_OVERVIEW.md) | This file | Project leads |

## Next Steps

1. **Read** [QUICKSTART.md](QUICKSTART.md) to get started
2. **Test** with manual run: `python auto_update_scheduler.py`
3. **Choose** automation method (cron, API, or manual)
4. **Setup** following appropriate guide
5. **Monitor** first few runs
6. **Relax** while your site stays fresh automatically! 🎉

---

**Questions?** Check the detailed guides or review the logs for troubleshooting.

**Feedback?** This is your project - customize the automation to fit your needs!
