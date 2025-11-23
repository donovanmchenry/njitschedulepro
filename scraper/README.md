# NJIT Course Schedule Scraper

Automated tool to download course schedule data from NJIT's Banner system for all subjects.

## Features

- 🤖 **Fully Automated**: Set it and forget it with cron jobs or scheduled tasks
- 📊 **Bulk Scraping**: Downloads all subjects automatically
- 💾 **Auto-Update**: Keeps your website's course catalog up-to-date
- 🔄 **Manual Triggers**: Update on-demand via API endpoints
- 📅 **Scheduled Updates**: Daily, weekly, or custom schedules
- 🔒 **Browser Automation**: Handles authentication seamlessly
- 📈 **Progress Logging**: Track scraping progress and history
- 💪 **Error Handling**: Retry logic and comprehensive error messages

## Installation

1. Make sure you have Python 3.7+ installed

2. Install Google Chrome (required for Selenium automation)

3. Install required Python dependencies:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install selenium requests
```

**Note**: The scraper uses browser automation (Selenium) because the NJIT API requires SAML authentication. Selenium will automatically download and manage the ChromeDriver.

## Usage

### Scrape All Subjects for the Current Term

```bash
python njit_selenium_scraper.py
```

This will:
- Open Chrome browser automatically
- Navigate to the NJIT course schedule page
- Fetch all available subjects
- Click through each subject and download its CSV
- Save CSV files to `data/scraped/` directory

### Scrape All Subjects for a Specific Term

```bash
python njit_selenium_scraper.py --term 202501
```

Term codes follow the format: `YYYYTT` where:
- `YYYY` = Year
- `TT` = Term (01 = Spring, 06 = Summer, 09 = Fall)

### Scrape a Single Subject

```bash
python njit_selenium_scraper.py --subject CS --term 202501
```

### Custom Output Directory

```bash
python njit_selenium_scraper.py --output /path/to/output
```

### Run in Headless Mode (No Visible Browser)

```bash
python njit_selenium_scraper.py --headless
```

### Adjust Delay Between Subjects

```bash
python njit_selenium_scraper.py --delay 3.0
```

This sets a 3-second delay between processing subjects (default is 2.0 seconds).

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--term` | Term code (e.g., 202501) | Current term |
| `--subject` | Single subject to scrape (e.g., CS) | All subjects |
| `--output` | Output directory for CSV files | `data/scraped` |
| `--delay` | Delay between subjects (seconds) | 2.0 |
| `--headless` | Run browser in headless mode (no visible window) | False |

## Output Format

CSV files are saved with the following naming convention:
```
Course_Schedule_{TERM}_{SUBJECT}_{TIMESTAMP}.csv
```

Example: `Course_Schedule_202501_CS_20250111_143022.csv`

### CSV Columns

- **TERM**: Term code
- **COURSE**: Course code (e.g., CS 100)
- **TITLE**: Course title
- **SECTION**: Section number
- **CRN**: Course Reference Number
- **DAYS**: Meeting days
- **TIMES**: Meeting times
- **LOCATION**: Room/building location
- **STATUS**: Enrollment status (Open/Closed)
- **MAX**: Maximum enrollment
- **NOW**: Current enrollment
- **INSTRUCTOR**: Instructor name
- **INSTRUCTION_METHOD**: Delivery mode (In-Person, Online, etc.)
- **CREDITS**: Credit hours
- **INFO_LINK**: Additional information link
- **COMMENTS**: Course comments

## How It Works

The scraper uses browser automation (Selenium with Chrome) to interact with the NJIT course schedule website:

1. Opens Chrome browser and navigates to the course schedule page
2. Waits for the page to fully load (including AngularJS initialization)
3. Selects the desired term from the dropdown
4. Reads the list of all subjects from the subject table
5. For each subject:
   - Clicks on the subject link
   - Waits for the course sections to load
   - Clicks the "Export as Excel" button to download the CSV
   - Waits for the download to complete
6. Saves all CSV files to the specified output directory

**Why Browser Automation?** The NJIT API endpoints require SAML authentication, so direct API calls don't work without logging in. Browser automation allows the scraper to work with the public course schedule page without needing authentication credentials.

## Integration with Your Application

You can import and use the scraper in your own Python code:

```python
from njit_selenium_scraper import NJITSeleniumScraper

# Initialize scraper
scraper = NJITSeleniumScraper(
    download_dir='data/scraped',
    headless=True  # Run without visible browser
)

# Scrape all subjects
scraper.scrape_all_subjects(term='202501', delay=2.0)

# Or scrape a specific subject
scraper.scrape_single_subject('CS', term='202501')
```

## Troubleshooting

### ChromeDriver Issues

If you get errors about ChromeDriver:
```bash
# Make sure Chrome is installed
# Selenium 4.15+ automatically manages ChromeDriver

# If issues persist, manually install ChromeDriver:
# macOS: brew install chromedriver
# Linux: apt-get install chromium-chromedriver
# Windows: Download from https://chromedriver.chromium.org/
```

### Browser Doesn't Open

If the browser doesn't open:
- Make sure Google Chrome is installed
- Try running without `--headless` to see what's happening
- Check Chrome version matches ChromeDriver version

### Page Load Timeout

If you get timeout errors:
- Check your internet connection
- Verify the NJIT site is accessible: https://generalssb-prod.ec.njit.edu/
- Increase timeout by editing the script (currently 60 seconds)
- The NJIT site may be temporarily down

### No Data Downloaded

If no CSVs are downloaded:
- Make sure the subject actually has courses for that term
- Try running with `--subject CS` first to test
- Check the download directory permissions

### Slow Performance

If scraping is slow:
- Use `--headless` mode (faster than visible browser)
- Reduce delay if comfortable: `--delay 1.0`
- The default 2-second delay is respectful to the server

## Automation

Want your website to automatically update with the latest course data?

### Quick Setup

```bash
# Run automated update (scrapes + updates catalog)
python auto_update_scheduler.py
```

This will:
1. Scrape all current course schedules
2. Backup your existing catalog
3. Update with fresh data
4. Ready for your API to reload

### Scheduled Updates

Set up automatic daily/weekly updates:

**Daily at 2 AM:**
```bash
# Add to crontab (crontab -e)
0 2 * * * cd /path/to/scraper && source venv/bin/activate && python auto_update_scheduler.py --headless
```

**See Full Automation Guide:** [AUTOMATION_SETUP.md](AUTOMATION_SETUP.md)

### API Integration

Trigger updates from your web interface:

```typescript
// Trigger update
await fetch('/admin/update-catalog', { method: 'POST' });

// Check status
await fetch('/admin/update-status');

// Reload catalog
await fetch('/admin/reload-catalog', { method: 'POST' });
```

**See API Integration Guide:** [API_INTEGRATION.md](API_INTEGRATION.md)

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 3 steps
- **[AUTOMATION_SETUP.md](AUTOMATION_SETUP.md)** - Complete automation guide (cron, systemd, launchd)
- **[API_INTEGRATION.md](API_INTEGRATION.md)** - Add admin endpoints to your API

## Notes

- This tool is for educational and research purposes
- Be respectful of NJIT's servers - use appropriate delays (2+ seconds recommended)
- The scraper only accesses publicly available course schedule data
- No NJIT login credentials are required
- Downloads are identical to manually clicking "Export as Excel" for each subject
- Headless mode is faster but visible mode helps with debugging

## Alternative: Direct API Scraper

The repository also includes `njit_course_scraper.py` which attempts to use the API directly. However, due to SAML authentication requirements, this approach doesn't work without credentials. Use `njit_selenium_scraper.py` instead for automated scraping.

## License

This tool is provided as-is for educational purposes.
