import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from njit_selenium_scraper import NJITSeleniumScraper
from auto_update_scheduler import ScheduleUpdater
from selenium.common.exceptions import TimeoutException


class DownloadVerificationTests(unittest.TestCase):
    def test_wait_for_download_requires_a_new_nonempty_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            download_dir = Path(directory)
            (download_dir / "existing.csv").write_text("header\n", encoding="utf-8")
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)

            def create_download():
                time.sleep(0.05)
                (download_dir / "new.csv").write_text("header\nvalue\n", encoding="utf-8")

            writer = threading.Thread(target=create_download)
            writer.start()
            downloaded = scraper.wait_for_download(
                previous_files={"existing.csv"},
                timeout=1,
                poll_interval=0.01,
            )
            writer.join()

            self.assertEqual(downloaded.name, "new.csv")

    def test_wait_for_download_times_out_when_click_produces_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)

            with self.assertRaisesRegex(TimeoutException, "No new CSV appeared"):
                scraper.wait_for_download(timeout=0.05, poll_interval=0.01)

    def test_incomplete_parallel_scrape_does_not_replace_catalog(self):
        class ImmediateFuture:
            def result(self):
                return 1

        class IncompleteExecutor:
            def __init__(self, max_workers):
                self.max_workers = max_workers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def submit(self, function, subjects, term, scrape_subdir, headless):
                worker_dir = Path(scrape_subdir)
                worker_dir.mkdir(parents=True, exist_ok=True)
                (worker_dir / "only-one.csv").write_text("header\n", encoding="utf-8")
                return ImmediateFuture()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            updater = ScheduleUpdater(
                scrape_dir=str(root / "scrape"),
                catalog_dir=str(root / "catalog"),
                workers=1,
            )

            with (
                patch.object(updater, "_get_all_subjects", return_value=["CS", "MATH"]),
                patch("auto_update_scheduler.ProcessPoolExecutor", IncompleteExecutor),
                patch("auto_update_scheduler.as_completed", side_effect=lambda futures: list(futures)),
            ):
                self.assertFalse(updater.scrape_latest_data())


if __name__ == "__main__":
    unittest.main()
