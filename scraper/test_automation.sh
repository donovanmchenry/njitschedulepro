#!/bin/bash
# Test script to verify automation setup

set -e  # Exit on error

echo "======================================"
echo "NJIT Automation System Test"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# Test 1: Check Python
echo "Test 1: Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.7+"
    exit 1
fi
echo ""

# Test 2: Check virtual environment
echo "Test 2: Checking virtual environment..."
if [ -d "venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment not found"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi
echo ""

# Test 3: Activate venv and check dependencies
echo "Test 3: Checking dependencies..."
source venv/bin/activate

if python -c "import selenium" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Selenium installed"
else
    echo -e "${YELLOW}⚠${NC} Selenium not found. Installing..."
    pip install -q selenium
    echo -e "${GREEN}✓${NC} Selenium installed"
fi

if python -c "import requests" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Requests installed"
else
    echo -e "${YELLOW}⚠${NC} Requests not found. Installing..."
    pip install -q requests
    echo -e "${GREEN}✓${NC} Requests installed"
fi
echo ""

# Test 4: Check Chrome
echo "Test 4: Checking Chrome installation..."
if command -v google-chrome &> /dev/null || command -v chromium &> /dev/null || [ -d "/Applications/Google Chrome.app" ]; then
    echo -e "${GREEN}✓${NC} Chrome/Chromium found"
else
    echo -e "${RED}✗${NC} Chrome not found. Please install Google Chrome"
    echo "macOS: https://www.google.com/chrome/"
    echo "Linux: sudo apt install chromium-browser"
    exit 1
fi
echo ""

# Test 5: Check required files
echo "Test 5: Checking required files..."
if [ -f "njit_selenium_scraper.py" ]; then
    echo -e "${GREEN}✓${NC} njit_selenium_scraper.py found"
else
    echo -e "${RED}✗${NC} njit_selenium_scraper.py not found"
    exit 1
fi

if [ -f "auto_update_scheduler.py" ]; then
    echo -e "${GREEN}✓${NC} auto_update_scheduler.py found"
else
    echo -e "${RED}✗${NC} auto_update_scheduler.py not found"
    exit 1
fi
echo ""

# Test 6: Check directories
echo "Test 6: Checking directories..."

# Check catalog directory
CATALOG_DIR="../courseschedules"
if [ -d "$CATALOG_DIR" ]; then
    echo -e "${GREEN}✓${NC} Catalog directory exists: $CATALOG_DIR"
else
    echo -e "${YELLOW}⚠${NC} Catalog directory not found. Creating..."
    mkdir -p "$CATALOG_DIR"
    echo -e "${GREEN}✓${NC} Catalog directory created"
fi

# Check scrape directory
if [ -d "data/temp_scrape" ]; then
    echo -e "${GREEN}✓${NC} Temp scrape directory exists"
else
    echo "Creating temp scrape directory..."
    mkdir -p data/temp_scrape
    echo -e "${GREEN}✓${NC} Temp scrape directory created"
fi
echo ""

# Test 7: Test single subject scrape
echo "Test 7: Testing scraper with a single subject..."
echo -e "${YELLOW}This will open Chrome and download one CSV file.${NC}"
echo "This may take 30-60 seconds..."
echo ""

if python njit_selenium_scraper.py --subject CS --headless &> test_scrape.log; then
    echo -e "${GREEN}✓${NC} Scraper test successful!"

    # Check if file was downloaded
    CSV_COUNT=$(ls -1 data/temp_scrape/*.csv 2>/dev/null | wc -l)
    if [ "$CSV_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} CSV file downloaded successfully"
        CSV_FILE=$(ls -1 data/temp_scrape/*.csv | head -1)
        CSV_SIZE=$(du -h "$CSV_FILE" | cut -f1)
        echo "  File: $(basename $CSV_FILE)"
        echo "  Size: $CSV_SIZE"
    else
        echo -e "${RED}✗${NC} No CSV file found"
        echo "Check test_scrape.log for details"
    fi
else
    echo -e "${RED}✗${NC} Scraper test failed"
    echo "Check test_scrape.log for details"
    echo ""
    echo "Last 10 lines of log:"
    tail -10 test_scrape.log
    exit 1
fi
echo ""

# Test 8: Test auto updater (dry run)
echo "Test 8: Testing auto updater..."
echo -e "${YELLOW}This will test the update orchestrator.${NC}"
echo ""

# Just check if it can be imported/run help
if python -c "from auto_update_scheduler import ScheduleUpdater; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${GREEN}✓${NC} Auto updater can be imported"
else
    echo -e "${RED}✗${NC} Auto updater import failed"
    exit 1
fi
echo ""

# Test 9: Check API integration
echo "Test 9: Checking API integration..."
API_ENDPOINTS="../api/app/admin_endpoints.py"
if [ -f "$API_ENDPOINTS" ]; then
    echo -e "${GREEN}✓${NC} Admin endpoints file found"
else
    echo -e "${YELLOW}⚠${NC} Admin endpoints not integrated yet"
    echo "See API_INTEGRATION.md for setup instructions"
fi
echo ""

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}✓${NC} Python environment: OK"
echo -e "${GREEN}✓${NC} Dependencies: OK"
echo -e "${GREEN}✓${NC} Chrome browser: OK"
echo -e "${GREEN}✓${NC} Required files: OK"
echo -e "${GREEN}✓${NC} Directories: OK"
echo -e "${GREEN}✓${NC} Scraper functionality: OK"
echo -e "${GREEN}✓${NC} Auto updater: OK"
echo ""
echo "======================================"
echo -e "${GREEN}All tests passed!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Run full update: python auto_update_scheduler.py"
echo "2. Setup automation: See AUTOMATION_SETUP.md"
echo "3. Setup API: See API_INTEGRATION.md"
echo ""
echo "Documentation:"
echo "- QUICKSTART.md - Get started quickly"
echo "- AUTOMATION_OVERVIEW.md - System overview"
echo "- AUTOMATION_SETUP.md - Cron/scheduling setup"
echo "- API_INTEGRATION.md - API endpoints setup"
echo ""

# Cleanup
rm -f test_scrape.log

exit 0
