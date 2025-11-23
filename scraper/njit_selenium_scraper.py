#!/usr/bin/env python3
"""
NJIT Course Schedule Scraper using Selenium
Automates browser interaction to download course schedule CSVs for all subjects.
"""

import time
import os
from pathlib import Path
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NJITSeleniumScraper:
    """Browser automation scraper for NJIT course schedules."""

    URL = "https://generalssb-prod.ec.njit.edu/BannerExtensibility/customPage/page/stuRegCrseSched"

    def __init__(self, download_dir: str = None, headless: bool = False):
        """
        Initialize the scraper.

        Args:
            download_dir: Directory for downloaded CSV files
            headless: Run browser in headless mode (no visible window)
        """
        if download_dir is None:
            download_dir = str(Path.cwd() / "data" / "scraped")

        self.download_dir = Path(download_dir).absolute()
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Setup Chrome options
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless=new')

        # Set download directory
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        self.options.add_experimental_option("prefs", prefs)

        # Additional options for stability
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)

        self.driver = None

    def start_driver(self):
        """Initialize and start the Chrome driver."""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.driver.set_page_load_timeout(120)  # Increased to 120 seconds
            logger.info("Chrome driver started successfully")
        except Exception as e:
            logger.error(f"Failed to start Chrome driver: {e}")
            logger.info("Make sure Chrome and ChromeDriver are installed")
            raise

    def stop_driver(self):
        """Stop and quit the Chrome driver."""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver stopped")

    def load_page(self, max_retries: int = 3):
        """Load the course schedule page with retry logic."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Loading page (attempt {attempt + 1}/{max_retries}): {self.URL}")
                self.driver.get(self.URL)

                # Wait for the page to load - wait for the term select dropdown
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.ID, "pbid-selectBlockTermSelect"))
                )
                logger.info("Page loaded successfully")
                time.sleep(3)  # Additional wait for AngularJS to initialize
                return  # Success!

            except TimeoutException as e:
                logger.warning(f"Page load timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    logger.info("Retrying page load...")
                    time.sleep(5)
                else:
                    logger.error("Page load failed after all retries")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error loading page: {e}")
                if attempt < max_retries - 1:
                    # Restart driver if session died
                    if "invalid session" in str(e).lower():
                        logger.info("Session died, restarting driver...")
                        try:
                            self.stop_driver()
                        except:
                            pass
                        time.sleep(2)
                        self.start_driver()
                    time.sleep(5)
                else:
                    raise

    def select_term(self, term: str = None):
        """
        Select a term from the dropdown.

        Args:
            term: Term code (e.g., '202501'). If None, uses default.
        """
        try:
            term_select = Select(self.driver.find_element(By.ID, "pbid-selectBlockTermSelect"))

            if term:
                term_select.select_by_value(term)
                logger.info(f"Selected term: {term}")
            else:
                # Use the default selected term
                selected_option = term_select.first_selected_option
                term_value = selected_option.get_attribute('value')
                logger.info(f"Using default term: {term_value}")

            time.sleep(2)  # Wait for data to load
        except Exception as e:
            logger.error(f"Failed to select term: {e}")
            raise

    def get_subjects(self):
        """
        Get list of all subject codes from the subject table.

        Returns:
            List of subject code strings
        """
        try:
            # Wait for subject table to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "pbid-subjListTable"))
            )

            # Find all subject link elements
            subject_table = self.driver.find_element(By.ID, "pbid-subjListTable")
            subject_links = subject_table.find_elements(By.CSS_SELECTOR, "tbody tr td a")

            subjects = [link.text.strip() for link in subject_links if link.text.strip()]

            logger.info(f"Found {len(subjects)} subjects")
            return subjects

        except Exception as e:
            logger.error(f"Failed to get subjects: {e}")
            return []

    def click_subject(self, subject_text: str):
        """
        Click on a subject in the subject list.

        Args:
            subject_text: The subject code to click (e.g., 'CS')
        """
        try:
            # Find and click the subject link
            subject_table = self.driver.find_element(By.ID, "pbid-subjListTable")
            subject_links = subject_table.find_elements(By.CSS_SELECTOR, "tbody tr td a")

            for link in subject_links:
                if link.text.strip() == subject_text:
                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    time.sleep(0.5)

                    try:
                        # Try normal click first
                        link.click()
                    except Exception as click_error:
                        # If normal click fails, try JavaScript click
                        logger.warning(f"Normal click failed for {subject_text}, trying JavaScript click")
                        self.driver.execute_script("arguments[0].click();", link)

                    logger.info(f"Clicked subject: {subject_text}")
                    time.sleep(1)  # Wait for sections to load
                    return True

            logger.warning(f"Subject not found: {subject_text}")
            return False

        except Exception as e:
            logger.error(f"Failed to click subject {subject_text}: {e}")
            return False

    def wait_for_sections_to_load(self):
        """Wait for course sections to finish loading."""
        try:
            # Wait for the loader to disappear
            WebDriverWait(self.driver, 30).until(
                EC.invisibility_of_element_located((By.ID, "loader"))
            )
            time.sleep(1)  # Additional buffer
        except TimeoutException:
            logger.warning("Timeout waiting for sections to load")

    def download_excel(self):
        """Click the 'Export as Excel' button to download CSV."""
        try:
            # Find and click the export button
            export_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "pbid-courseListSectionExportToExcel"))
            )

            export_button.click()
            logger.info("Clicked 'Export as Excel' button")
            time.sleep(2)  # Wait for download to start

        except Exception as e:
            logger.error(f"Failed to click export button: {e}")
            raise

    def wait_for_download(self, timeout: int = 30):
        """
        Wait for a download to complete.

        Args:
            timeout: Maximum seconds to wait
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if any .crdownload files exist (Chrome incomplete downloads)
            incomplete = list(self.download_dir.glob("*.crdownload"))
            if not incomplete:
                time.sleep(0.5)
                return True
            time.sleep(0.5)

        logger.warning("Download may not have completed")
        return False

    def _restart_browser(self, term: str = None):
        """Helper method to restart the browser session."""
        try:
            logger.info("Restarting browser session...")
            self.stop_driver()
            time.sleep(2)
            self.start_driver()
            self.load_page()
            self.select_term(term)
            # Extra wait for page to fully settle after restart
            time.sleep(5)
            logger.info("Browser restarted successfully")
            return True
        except Exception as e:
            logger.error(f"Error restarting browser: {e}")
            return False

    def scrape_all_subjects(self, term: str = None, delay: float = 2.0, restart_interval: int = 12):
        """
        Scrape all subjects for a term with automatic browser restarts and error recovery.

        Args:
            term: Term code (e.g., '202501'). If None, uses default.
            delay: Delay in seconds between subjects
            restart_interval: Restart browser after this many subjects to avoid timeouts
        """
        try:
            # Start the browser
            self.start_driver()

            # Load the page
            self.load_page()

            # Select term
            self.select_term(term)

            # Get all subjects
            subjects = self.get_subjects()
            if not subjects:
                logger.error("No subjects found")
                return

            total = len(subjects)
            successful = 0
            failed = []
            subjects_since_restart = 0

            logger.info(f"Starting to scrape {total} subjects...")
            logger.info(f"Browser will restart every {restart_interval} subjects to prevent timeouts")

            # Process each subject
            for i, subject in enumerate(subjects, 1):
                logger.info(f"Processing {i}/{total}: {subject}")

                # Check if we need to do a scheduled restart
                if subjects_since_restart >= restart_interval and i < total:
                    logger.info(f"{'='*60}")
                    logger.info(f"Scheduled restart after {subjects_since_restart} subjects...")
                    logger.info(f"{'='*60}")

                    self._restart_browser(term)
                    subjects_since_restart = 0
                    time.sleep(2)

                # Try to process the subject with retry logic
                max_retries = 2
                retry_count = 0
                subject_success = False

                while retry_count < max_retries and not subject_success:
                    try:
                        # Click the subject
                        if not self.click_subject(subject):
                            logger.warning(f"Could not find subject: {subject}")
                            break

                        # Wait for sections to load
                        self.wait_for_sections_to_load()

                        # Download Excel/CSV
                        self.download_excel()

                        # Wait for download to complete
                        self.wait_for_download()

                        successful += 1
                        subjects_since_restart += 1
                        subject_success = True
                        logger.info(f"Successfully downloaded {subject}")

                    except Exception as e:
                        error_msg = str(e)

                        # Check if it's a session error
                        if "invalid session" in error_msg.lower() or "session deleted" in error_msg.lower():
                            logger.error(f"Session error detected for {subject}. Browser crashed unexpectedly.")

                            # Restart browser immediately
                            logger.info(f"{'='*60}")
                            logger.info(f"Emergency restart due to session failure...")
                            logger.info(f"{'='*60}")

                            if self._restart_browser(term):
                                subjects_since_restart = 0
                                retry_count += 1

                                if retry_count < max_retries:
                                    logger.info(f"Retrying {subject} (attempt {retry_count + 1}/{max_retries})")
                                    time.sleep(2)
                                    continue
                            else:
                                logger.error("Failed to restart browser. Aborting.")
                                raise
                        else:
                            logger.error(f"Error processing {subject}: {e}")

                        retry_count += 1
                        if retry_count >= max_retries:
                            break
                        time.sleep(2)

                # Mark as failed if we didn't succeed
                if not subject_success:
                    failed.append(subject)
                    # Still increment counter to avoid getting stuck
                    subjects_since_restart += 1

                # Delay between requests
                if i < total:
                    time.sleep(delay)

            # Summary
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping complete!")
            logger.info(f"Successful: {successful}/{total}")
            if failed:
                logger.info(f"Failed ({len(failed)}): {', '.join(failed)}")
            logger.info(f"Files saved to: {self.download_dir}")
            logger.info(f"{'='*60}")

        finally:
            # Always stop the driver
            self.stop_driver()

    def scrape_single_subject(self, subject: str, term: str = None):
        """
        Scrape a single subject.

        Args:
            subject: Subject code (e.g., 'CS')
            term: Term code (e.g., '202501'). If None, uses default.
        """
        try:
            self.start_driver()
            self.load_page()
            self.select_term(term)

            logger.info(f"Scraping subject: {subject}")

            if self.click_subject(subject):
                self.wait_for_sections_to_load()
                self.download_excel()
                self.wait_for_download()
                logger.info(f"Successfully downloaded {subject}")
            else:
                logger.error(f"Failed to find subject: {subject}")

        finally:
            self.stop_driver()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape NJIT course schedules using browser automation')
    parser.add_argument('--term', type=str, help='Term code (e.g., 202501)', default=None)
    parser.add_argument('--subject', type=str, help='Single subject to scrape (e.g., CS)', default=None)
    parser.add_argument('--output', type=str, help='Output directory', default='data/scraped')
    parser.add_argument('--delay', type=float, help='Delay between subjects in seconds', default=2.0)
    parser.add_argument('--restart-interval', type=int, help='Restart browser after N subjects (default: 12)', default=12)
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')

    args = parser.parse_args()

    scraper = NJITSeleniumScraper(
        download_dir=args.output,
        headless=args.headless
    )

    if args.subject:
        # Scrape single subject
        scraper.scrape_single_subject(args.subject, args.term)
    else:
        # Scrape all subjects
        scraper.scrape_all_subjects(term=args.term, delay=args.delay, restart_interval=args.restart_interval)


if __name__ == '__main__':
    main()
