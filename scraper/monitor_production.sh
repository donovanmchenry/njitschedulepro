#!/bin/bash
# Monitor production scraper progress

echo "Monitoring production scraper..."
echo "Press Ctrl+C to stop monitoring (scraper will continue running)"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "PRODUCTION SCRAPER STATUS"
    echo "=========================================="
    echo "Time: $(date '+%H:%M:%S')"
    echo ""
    
    # Get current progress
    CURRENT=$(grep -c "Successfully downloaded" production_test.log 2>/dev/null || echo "0")
    echo "Progress: $CURRENT/120 subjects downloaded"
    
    # Show recent activity
    echo ""
    echo "Recent activity:"
    tail -5 production_test.log 2>/dev/null || echo "Log not found"
    
    echo ""
    echo "=========================================="
    
    sleep 5
done
