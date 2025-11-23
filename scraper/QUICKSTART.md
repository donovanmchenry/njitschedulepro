# Quick Start Guide

Get started scraping NJIT course schedules in 3 simple steps!

## Step 1: Install Dependencies

```bash
# Navigate to the scraper directory
cd /Users/donovanmchenry/Projects/njitschedulepro/scraper

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

## Step 2: Run the Scraper

### Test with a Single Subject First

```bash
python njit_selenium_scraper.py --subject CS
```

This will:
- Open Chrome browser
- Navigate to the NJIT course schedule
- Download the CSV for Computer Science courses
- Save to `data/scraped/` directory

### Scrape All Subjects

Once you've verified it works, scrape everything:

```bash
python njit_selenium_scraper.py
```

This will download CSVs for **all** subjects (50+). It takes about 5-10 minutes.

### Run in Background (Headless Mode)

```bash
python njit_selenium_scraper.py --headless
```

No browser window will appear - perfect for running unattended.

## Step 3: Find Your Data

CSV files will be in `data/scraped/`:

```bash
ls -lh data/scraped/
```

Example files:
- `Course_Schedule_202501_CS_20250111_143022.csv`
- `Course_Schedule_202501_MATH_20250111_143045.csv`
- etc.

## Common Use Cases

### Scrape Spring 2025

```bash
python njit_selenium_scraper.py --term 202501
```

### Scrape Just a Few Subjects

```bash
# Run these one at a time
python njit_selenium_scraper.py --subject CS
python njit_selenium_scraper.py --subject MATH
python njit_selenium_scraper.py --subject PHYS
```

### Save to Custom Location

```bash
python njit_selenium_scraper.py --output ~/Downloads/njit_courses
```

### Be Extra Polite to Server

```bash
python njit_selenium_scraper.py --delay 5.0
```

Waits 5 seconds between each subject (default is 2 seconds).

## Term Codes Reference

| Term | Code |
|------|------|
| Spring 2025 | 202501 |
| Summer 2025 | 202506 |
| Fall 2025 | 202509 |
| Spring 2026 | 202601 |

Format: `YYYYTT` where `TT` is `01` (Spring), `06` (Summer), or `09` (Fall)

## Troubleshooting

### "ChromeDriver not found"

Make sure Google Chrome is installed. Selenium 4.15+ handles ChromeDriver automatically.

### "No module named 'selenium'"

You forgot to activate the virtual environment or install dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Page won't load

- Check your internet connection
- Try visiting https://generalssb-prod.ec.njit.edu/ in your browser
- The NJIT site may be temporarily down

### Need Help?

See the full [README.md](README.md) for detailed documentation.

## What's Next?

Once you have the CSV files, you can:
1. Import them into your database
2. Use them in your web application
3. Analyze course availability patterns
4. Build schedule optimization tools

Enjoy your automated course scraping! 🎓
