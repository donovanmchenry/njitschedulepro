#!/bin/bash
# Retry failed subjects individually

FAILED_SUBJECTS="HSS ID IE IET INT INTD IS IT LIT MARC MATH ME TUTR USYS YWCC"

for subject in $FAILED_SUBJECTS; do
  echo "================================================================"
  echo "Scraping $subject..."
  echo "================================================================"
  ./venv/bin/python njit_selenium_scraper.py --headless --subject "$subject" --output data/temp_scrape
  sleep 3
done

echo "================================================================"
echo "Retry scraping complete!"
echo "================================================================"
echo ""
echo "Checking final count..."
ls data/temp_scrape/*.csv | wc -l
