#!/usr/bin/env python3
"""
Automated scheduler for NJIT course schedule scraping and database updates.
Uses parallel Selenium browser instances for ~3x speedup over sequential scraping.
"""

import os
import sys
import shutil
import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from typing import Optional, List

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


def _worker(
    subjects: List[str],
    term: Optional[str],
    scrape_subdir: str,
    headless: bool,
    restart_interval: int,
) -> int:
    """
    Top-level worker function (must be module-level for multiprocessing pickling).
    Runs a Selenium scraper for a chunk of subjects and returns the CSV count.
    """
    # Each worker gets its own logger to avoid interleaving
    import logging as _logging
    worker_logger = _logging.getLogger(f"worker-{os.getpid()}")

    Path(scrape_subdir).mkdir(parents=True, exist_ok=True)
    scraper = NJITSeleniumScraper(download_dir=scrape_subdir, headless=headless)
    scraper.scrape_subject_list(
        subjects=subjects,
        term=term,
        delay=1.0,
        restart_interval=restart_interval,
    )
    return len(list(Path(scrape_subdir).glob("*.csv")))


class ScheduleUpdater:
    """Automated course schedule updater with parallel browser support."""

    MAX_RECOVERY_SUBJECTS = 20
    RECOVERY_COOLDOWN_SECONDS = 20

    def __init__(
        self,
        scrape_dir: str = None,
        catalog_dir: str = None,
        headless: bool = True,
        workers: int = 3,
    ):
        """
        Initialize the updater.

        Args:
            scrape_dir: Temporary directory for scraped files
            catalog_dir: Directory where API reads CSVs from
            headless: Run scraper in headless mode
            workers: Number of parallel Chrome instances (default 3)
        """
        if scrape_dir is None:
            scrape_dir = str(Path(__file__).parent / "data" / "temp_scrape")
        if catalog_dir is None:
            catalog_dir = str(Path(__file__).parent.parent / "courseschedules")

        self.scrape_dir = Path(scrape_dir)
        self.catalog_dir = Path(catalog_dir)
        self.headless = headless
        self.workers = workers

        self.scrape_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Scrape directory: {self.scrape_dir}")
        logger.info(f"Catalog directory: {self.catalog_dir}")
        logger.info(f"Parallel workers: {self.workers}")

    def _get_all_subjects(self, term: Optional[str]) -> List[str]:
        """
        Use a single Selenium instance to load the page and retrieve the full
        subject list, then quit immediately.
        """
        logger.info("Fetching subject list...")
        scraper = NJITSeleniumScraper(download_dir=str(self.scrape_dir), headless=self.headless)
        try:
            scraper.start_driver()
            scraper.load_page()
            scraper.select_term(term)
            subjects = scraper.get_subjects()
            return subjects
        finally:
            scraper.stop_driver()

    @staticmethod
    def _subject_code_from_csv(csv_file: Path) -> Optional[str]:
        """Extract the subject code from an NJIT schedule export filename."""
        parts = csv_file.stem.split("_")
        if len(parts) < 5 or parts[:2] != ["Course", "Schedule"]:
            return None
        return parts[3]

    def _missing_subjects(self, subjects: List[str]) -> List[str]:
        downloaded = {
            code
            for csv_file in self.scrape_dir.glob("*.csv")
            if (code := self._subject_code_from_csv(csv_file)) is not None
        }
        return [subject for subject in subjects if subject not in downloaded]

    def _recover_missing_subjects(
        self,
        subjects: List[str],
        term: Optional[str],
    ) -> None:
        """Retry a small number of missed exports with one fresh browser."""
        if not subjects:
            return

        logger.warning(
            f"Retrying {len(subjects)} missed subjects sequentially after "
            f"a {self.RECOVERY_COOLDOWN_SECONDS}-second cooldown: "
            f"{', '.join(subjects)}"
        )
        time.sleep(self.RECOVERY_COOLDOWN_SECONDS)

        recovery_dir = self.scrape_dir / "recovery"
        shutil.rmtree(recovery_dir, ignore_errors=True)
        recovery_dir.mkdir(parents=True, exist_ok=True)

        scraper = NJITSeleniumScraper(
            download_dir=str(recovery_dir),
            headless=self.headless,
        )
        scraper.scrape_subject_list(
            subjects=subjects,
            term=term,
            delay=3.0,
            restart_interval=0,
        )

        for csv_file in recovery_dir.glob("*.csv"):
            shutil.move(str(csv_file), str(self.scrape_dir / csv_file.name))

    def scrape_latest_data(self, term: Optional[str] = None) -> bool:
        """
        Run parallel Selenium workers to scrape all subjects concurrently.

        Strategy:
          1. One browser fetches the subject list (then quits).
          2. Subjects are split into `workers` interleaved chunks so each worker
             gets a balanced mix (interleaved avoids all workers hitting large
             departments at the same time).
          3. Each worker writes CSVs to its own subdirectory to avoid conflicts.
          4. All CSVs are merged into self.scrape_dir when workers finish.
        """
        logger.info("=" * 60)
        logger.info(f"Starting parallel scrape ({self.workers} workers)...")
        logger.info("=" * 60)

        try:
            # Clear temp directory
            if self.scrape_dir.exists():
                for f in self.scrape_dir.glob("*.csv"):
                    f.unlink()
                for d in self.scrape_dir.glob("worker_*"):
                    shutil.rmtree(d, ignore_errors=True)
                shutil.rmtree(self.scrape_dir / "recovery", ignore_errors=True)

            # Step 1: Get subject list
            subjects = self._get_all_subjects(term)
            if not subjects:
                logger.error("No subjects found")
                return False
            logger.info(f"Total subjects to scrape: {len(subjects)}")

            # Step 2: Split into interleaved chunks
            # Interleaved (round-robin) gives balanced chunks even if dept sizes vary
            chunks = [subjects[i::self.workers] for i in range(self.workers)]
            for i, chunk in enumerate(chunks):
                logger.info(f"  Worker {i+1}: {len(chunk)} subjects")

            # Step 3: Run workers in parallel
            subdirs = [str(self.scrape_dir / f"worker_{i}") for i in range(self.workers)]
            # Keep browser sessions bounded without restarting every worker at once.
            restart_intervals = [20 + (4 * i) for i in range(self.workers)]

            with ProcessPoolExecutor(max_workers=self.workers) as executor:
                futures = {
                    executor.submit(
                        _worker,
                        chunk,
                        term,
                        subdir,
                        self.headless,
                        restart_intervals[i],
                    ): i
                    for i, (chunk, subdir) in enumerate(zip(chunks, subdirs))
                }
                for future in as_completed(futures):
                    worker_idx = futures[future]
                    try:
                        count = future.result()
                        logger.info(f"Worker {worker_idx + 1} finished: {count} CSVs")
                    except Exception as e:
                        logger.error(f"Worker {worker_idx + 1} failed: {e}", exc_info=True)

            # Step 4: Merge all worker CSVs into scrape_dir
            merged = 0
            for subdir in subdirs:
                for csv_file in Path(subdir).glob("*.csv"):
                    shutil.move(str(csv_file), str(self.scrape_dir / csv_file.name))
                    merged += 1

            if merged == 0:
                logger.error("No CSV files were produced by any worker!")
                return False

            missing = self._missing_subjects(subjects)
            if 0 < len(missing) <= self.MAX_RECOVERY_SUBJECTS:
                self._recover_missing_subjects(missing, term)
                missing = self._missing_subjects(subjects)

            if missing:
                logger.error(
                    "Incomplete scrape: missing "
                    f"{len(missing)} of {len(subjects)} subjects: "
                    f"{', '.join(missing)}. "
                    "The existing catalog will not be replaced."
                )
                return False

            final_count = len(list(self.scrape_dir.glob("*.csv")))
            logger.info(f"Merged {final_count} CSV files into {self.scrape_dir}")
            return True

        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            return False

    def update_catalog(self, backup: bool = True) -> bool:
        """
        Update the catalog directory with newly scraped files.
        """
        logger.info("=" * 60)
        logger.info("Updating catalog directory...")
        logger.info("=" * 60)

        try:
            if backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_dir = self.catalog_dir.parent / f"courseschedules_backup_{timestamp}"
                if list(self.catalog_dir.glob("*.csv")):
                    shutil.copytree(self.catalog_dir, backup_dir)
                    logger.info(f"Backed up existing catalog to: {backup_dir}")

            for file in self.catalog_dir.glob("*.csv"):
                file.unlink()
            logger.info("Cleared current catalog directory")

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

            metadata_file = self.catalog_dir / "_update_metadata.txt"
            with open(metadata_file, 'w') as f:
                f.write(f"Last Updated: {datetime.now().isoformat()}\n")
                f.write(f"File Count: {copied}\n")
                f.write(f"Update Method: Parallel Selenium ({self.workers} workers)\n")

            logger.info("Catalog update complete!")
            return True

        except Exception as e:
            logger.error(f"Error updating catalog: {e}", exc_info=True)
            return False

    def run_update_cycle(
        self,
        term: Optional[str] = None,
        backup: bool = True,
    ) -> bool:
        """
        Run a complete update cycle: scrape → update catalog.
        """
        start_time = time.time()
        logger.info("\n" + "=" * 60)
        logger.info("STARTING AUTOMATED UPDATE CYCLE")
        logger.info("=" * 60)
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Term: {term or 'Default (current term)'}")

        try:
            if not self.scrape_latest_data(term):
                logger.error("Scraping failed! Aborting update.")
                return False

            if not self.update_catalog(backup):
                logger.error("Catalog update failed! Aborting.")
                return False

            elapsed = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("UPDATE CYCLE COMPLETED SUCCESSFULLY")
            logger.info(f"Total time: {elapsed:.2f} seconds ({elapsed/60:.1f} min)")
            logger.info("=" * 60 + "\n")

            return True

        except Exception as e:
            logger.error(f"Update cycle failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point for manual or scheduled runs."""
    import argparse

    parser = argparse.ArgumentParser(description='Automated NJIT schedule updater (parallel)')
    parser.add_argument('--term', type=str, help='Term code (e.g., 202601)', default=None)
    parser.add_argument('--no-backup', action='store_true', help='Skip backing up existing catalog')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--workers', type=int, default=3, help='Number of parallel Chrome instances (default: 3)')
    parser.add_argument('--scrape-dir', type=str, help='Temporary scrape directory')
    parser.add_argument('--catalog-dir', type=str, help='Catalog directory (where API reads from)')

    args = parser.parse_args()

    updater = ScheduleUpdater(
        scrape_dir=args.scrape_dir,
        catalog_dir=args.catalog_dir,
        headless=not args.visible,
        workers=args.workers,
    )

    success = updater.run_update_cycle(
        term=args.term,
        backup=not args.no_backup,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
