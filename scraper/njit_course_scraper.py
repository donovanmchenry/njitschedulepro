#!/usr/bin/env python3
"""
NJIT Course Schedule Scraper
Automates downloading course schedule data for all subjects from NJIT's Banner system.
"""

import requests
import csv
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NJITCourseScraper:
    """Scraper for NJIT course schedule data."""

    BASE_URL = "https://generalssb-prod.ec.njit.edu/BannerExtensibility"

    def __init__(self, output_dir: str = "data/scraped"):
        """Initialize the scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_default_term(self) -> str:
        """Fetch the default term from the API."""
        url = f"{self.BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedDefaultTerm"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()

            if data and 'data' in data and len(data['data']) > 0:
                default_term = data['data'][0].get('DEFAULT_TERM')
                logger.info(f"Default term: {default_term}")
                return default_term
            else:
                logger.error("Could not find default term in response")
                return None
        except Exception as e:
            logger.error(f"Error fetching default term: {e}")
            return None

    def get_subjects(self, term: str, attr: str = "") -> List[Dict[str, Any]]:
        """Fetch all subjects for a given term."""
        url = f"{self.BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedSubjList"
        params = {
            'term': term,
            'attr': attr
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data and 'data' in data:
                subjects = data['data']
                logger.info(f"Found {len(subjects)} subjects")
                return subjects
            else:
                logger.error("No subjects found in response")
                return []
        except Exception as e:
            logger.error(f"Error fetching subjects: {e}")
            return []

    def get_sections(self, term: str, subject: str, attr: str = "") -> List[Dict[str, Any]]:
        """Fetch all sections for a given term and subject."""
        url = f"{self.BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedSectionsExcel"
        params = {
            'term': term,
            'subject': subject,
            'attr': attr,
            'prof_ucid': ''
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data and 'data' in data:
                sections = data['data']
                logger.info(f"Found {len(sections)} sections for {subject}")
                return sections
            else:
                logger.warning(f"No sections found for {subject}")
                return []
        except Exception as e:
            logger.error(f"Error fetching sections for {subject}: {e}")
            return []

    def save_to_csv(self, sections: List[Dict[str, Any]], filename: str):
        """Save sections data to a CSV file."""
        if not sections:
            logger.warning(f"No data to save to {filename}")
            return

        # Define the CSV columns based on the JavaScript code
        fieldnames = [
            'TERM', 'COURSE', 'TITLE', 'SECTION', 'CRN', 'DAYS', 'TIMES',
            'LOCATION', 'STATUS', 'MAX', 'NOW', 'INSTRUCTOR',
            'INSTRUCTION_METHOD', 'CREDITS', 'INFO_LINK', 'COMMENTS'
        ]

        filepath = self.output_dir / filename

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for section in sections:
                    # Only write fields that exist
                    row = {k: section.get(k, '') for k in fieldnames}
                    writer.writerow(row)

            logger.info(f"Saved {len(sections)} sections to {filepath}")
        except Exception as e:
            logger.error(f"Error saving CSV {filename}: {e}")

    def scrape_all_subjects(self, term: str = None, delay: float = 0.5):
        """
        Scrape all subjects for a term and save to individual CSV files.

        Args:
            term: The term code (e.g., '202501'). If None, uses default term.
            delay: Delay in seconds between requests to avoid overwhelming the server.
        """
        # Get default term if not provided
        if not term:
            term = self.get_default_term()
            if not term:
                logger.error("Could not determine term. Please provide term explicitly.")
                return

        logger.info(f"Starting scrape for term: {term}")

        # Fetch all subjects
        subjects = self.get_subjects(term)
        if not subjects:
            logger.error("No subjects to scrape")
            return

        # Track statistics
        total_subjects = len(subjects)
        successful = 0
        failed = 0

        # Process each subject
        for i, subject_data in enumerate(subjects, 1):
            subject_code = subject_data.get('SUBJECT', '')

            logger.info(f"Processing {i}/{total_subjects}: {subject_code}")

            # Fetch sections for this subject
            sections = self.get_sections(term, subject_code)

            if sections:
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"Course_Schedule_{term}_{subject_code}_{timestamp}.csv"

                # Save to CSV
                self.save_to_csv(sections, filename)
                successful += 1
            else:
                logger.warning(f"No sections found for {subject_code}")
                failed += 1

            # Be nice to the server
            if i < total_subjects:
                time.sleep(delay)

        logger.info(f"Scraping complete! Successful: {successful}, Failed: {failed}")
        logger.info(f"Files saved to: {self.output_dir.absolute()}")

    def scrape_single_subject(self, term: str, subject: str):
        """Scrape a single subject."""
        logger.info(f"Scraping {subject} for term {term}")

        sections = self.get_sections(term, subject)

        if sections:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Course_Schedule_{term}_{subject}_{timestamp}.csv"
            self.save_to_csv(sections, filename)
            logger.info(f"Successfully scraped {subject}")
        else:
            logger.error(f"Failed to scrape {subject}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape NJIT course schedule data')
    parser.add_argument('--term', type=str, help='Term code (e.g., 202501)', default=None)
    parser.add_argument('--subject', type=str, help='Single subject to scrape (e.g., CS)', default=None)
    parser.add_argument('--output', type=str, help='Output directory', default='data/scraped')
    parser.add_argument('--delay', type=float, help='Delay between requests in seconds', default=0.5)

    args = parser.parse_args()

    scraper = NJITCourseScraper(output_dir=args.output)

    if args.subject:
        # Scrape single subject
        term = args.term or scraper.get_default_term()
        if term:
            scraper.scrape_single_subject(term, args.subject)
    else:
        # Scrape all subjects
        scraper.scrape_all_subjects(term=args.term, delay=args.delay)


if __name__ == '__main__':
    main()
