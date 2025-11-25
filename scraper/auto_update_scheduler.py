#!/usr/bin/env python3
"""
Automated scheduler for NJIT course schedule scraping and database updates.
Runs scraper periodically and updates the API's course catalog.
"""

import os
import sys
import shutil
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from njit_selenium_scraper import NJITSeleniumScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScheduleUpdater:
    """Automated course schedule updater."""

    def __init__(
        self,
        scrape_dir: str = None,
        catalog_dir: str = None,
        headless: bool = True
    ):
        """
        Initialize the updater.

        Args:
            scrape_dir: Temporary directory for scraped files
            catalog_dir: Directory where API reads CSVs from
            headless: Run scraper in headless mode
        """
        # Default directories
        if scrape_dir is None:
            scrape_dir = str(Path(__file__).parent / "data" / "temp_scrape")
        if catalog_dir is None:
            # Default to ../courseschedules relative to scraper directory
            catalog_dir = str(Path(__file__).parent.parent / "courseschedules")

        self.scrape_dir = Path(scrape_dir)
        self.catalog_dir = Path(catalog_dir)
        self.headless = headless

        # Ensure directories exist
        self.scrape_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Scrape directory: {self.scrape_dir}")
        logger.info(f"Catalog directory: {self.catalog_dir}")

    def scrape_latest_data(self, term: Optional[str] = None) -> bool:
        """
        Run the scraper to get latest data.

        Args:
            term: Optional term code (e.g., '202501')

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Starting course schedule scrape...")
        logger.info("=" * 60)

        try:
            # Clear temp directory
            if self.scrape_dir.exists():
                for file in self.scrape_dir.glob("*.csv"):
                    file.unlink()
                logger.info("Cleared temporary scrape directory")

            # Run scraper
            scraper = NJITSeleniumScraper(
                download_dir=str(self.scrape_dir),
                headless=self.headless
            )

            scraper.scrape_all_subjects(term=term, delay=2.0, restart_interval=12)

            # Check if files were downloaded
            csv_files = list(self.scrape_dir.glob("*.csv"))
            if not csv_files:
                logger.error("No CSV files were downloaded!")
                return False

            logger.info(f"Successfully scraped {len(csv_files)} CSV files")
            return True

        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            return False

    def update_catalog(self, backup: bool = True) -> bool:
        """
        Update the catalog directory with newly scraped files.

        Args:
            backup: Whether to backup existing catalog first

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Updating catalog directory...")
        logger.info("=" * 60)

        try:
            # Backup existing catalog if requested
            if backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_dir = self.catalog_dir.parent / f"courseschedules_backup_{timestamp}"

                if list(self.catalog_dir.glob("*.csv")):
                    shutil.copytree(self.catalog_dir, backup_dir)
                    logger.info(f"Backed up existing catalog to: {backup_dir}")

            # Clear current catalog
            for file in self.catalog_dir.glob("*.csv"):
                file.unlink()
            logger.info("Cleared current catalog directory")

            # Copy new files
            csv_files = list(self.scrape_dir.glob("*.csv"))
            if not csv_files:
                logger.error("No CSV files to copy to catalog!")
                return False

            copied = 0
            for file in csv_files:
                dest = self.catalog_dir / file.name
                shutil.copy2(file, dest)
                copied += 1

            logger.info(f"Copied {copied} CSV files to catalog directory")

            # Create metadata file
            metadata_file = self.catalog_dir / "_update_metadata.txt"
            with open(metadata_file, 'w') as f:
                f.write(f"Last Updated: {datetime.now().isoformat()}\n")
                f.write(f"File Count: {copied}\n")
                f.write(f"Update Method: Automated Scraper\n")

            logger.info("Catalog update complete!")
            return True

        except Exception as e:
            logger.error(f"Error updating catalog: {e}", exc_info=True)
            return False

    def trigger_api_reload(self, api_url: str = "http://localhost:8000") -> bool:
        """
        Trigger API to reload catalog (requires API restart or reload endpoint).

        Args:
            api_url: Base URL of the API

        Returns:
            True if successful, False otherwise
        """
        try:
            import requests

            # Check if API is running
            response = requests.get(f"{api_url}/", timeout=5)
            if response.status_code == 200:
                logger.info("API is running. Catalog will be reloaded on next API restart.")
                logger.info("To reload immediately, restart the API with: uvicorn app.main:app --reload")
                return True
            else:
                logger.warning(f"API returned status code: {response.status_code}")
                return False

        except ImportError:
            logger.info("requests library not available, skipping API check")
            logger.info("API will load new catalog on next startup")
            return False
        except Exception as e:
            logger.warning(f"Could not connect to API at {api_url}: {e}")
            logger.info("API will load new catalog on next startup")
            return False

    def run_update_cycle(
        self,
        term: Optional[str] = None,
        backup: bool = True,
        api_url: str = "http://localhost:8000"
    ) -> bool:
        """
        Run a complete update cycle: scrape → update catalog → notify API.

        Args:
            term: Optional term code
            backup: Whether to backup existing catalog
            api_url: API base URL

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        logger.info("\n" + "=" * 60)
        logger.info("STARTING AUTOMATED UPDATE CYCLE")
        logger.info("=" * 60)
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Term: {term or 'Default (current term)'}")

        try:
            # Step 1: Scrape
            if not self.scrape_latest_data(term):
                logger.error("Scraping failed! Aborting update.")
                return False

            # Step 2: Update catalog
            if not self.update_catalog(backup):
                logger.error("Catalog update failed! Aborting.")
                return False

            # Step 3: Notify API
            self.trigger_api_reload(api_url)

            # Success
            elapsed = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("UPDATE CYCLE COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Total time: {elapsed:.2f} seconds")
            logger.info(f"Next steps:")
            logger.info(f"  1. Restart your API: uvicorn app.main:app --reload")
            logger.info(f"  2. Or wait for auto-reload if running in dev mode")
            logger.info("=" * 60 + "\n")

            return True

        except Exception as e:
            logger.error(f"Update cycle failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point for manual or scheduled runs."""
    import argparse

    parser = argparse.ArgumentParser(description='Automated NJIT schedule updater')
    parser.add_argument('--term', type=str, help='Term code (e.g., 202501)', default=None)
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backing up existing catalog'
    )
    parser.add_argument(
        '--visible',
        action='store_true',
        help='Run browser in visible mode (not headless)'
    )
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8000',
        help='API base URL'
    )
    parser.add_argument(
        '--scrape-dir',
        type=str,
        help='Temporary scrape directory'
    )
    parser.add_argument(
        '--catalog-dir',
        type=str,
        help='Catalog directory (where API reads from)'
    )

    args = parser.parse_args()

    # Create updater
    updater = ScheduleUpdater(
        scrape_dir=args.scrape_dir,
        catalog_dir=args.catalog_dir,
        headless=not args.visible
    )

    # Run update cycle
    success = updater.run_update_cycle(
        term=args.term,
        backup=not args.no_backup,
        api_url=args.api_url
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
