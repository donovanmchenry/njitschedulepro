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

            def submit(
                self,
                function,
                subjects,
                term,
                scrape_subdir,
                headless,
                restart_interval,
            ):
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
            updater.MAX_RECOVERY_SUBJECTS = 0

            with (
                patch.object(updater, "_get_all_subjects", return_value=["CS", "MATH"]),
                patch("auto_update_scheduler.ProcessPoolExecutor", IncompleteExecutor),
                patch("auto_update_scheduler.as_completed", side_effect=lambda futures: list(futures)),
            ):
                self.assertFalse(updater.scrape_latest_data())

    def test_missing_subjects_are_identified_from_export_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            updater = ScheduleUpdater(
                scrape_dir=str(root / "scrape"),
                catalog_dir=str(root / "catalog"),
                workers=1,
            )
            (updater.scrape_dir / "Course_Schedule_202690_CS_202691_1200.csv").write_text(
                "header\n",
                encoding="utf-8",
            )

            self.assertEqual(updater._missing_subjects(["CS", "MATH"]), ["MATH"])

    def test_click_subject_propagates_a_dead_browser_session(self):
        class DeadDriver:
            def find_element(self, *args, **kwargs):
                raise RuntimeError("invalid session id: disconnected from DevTools")

        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
            scraper.driver = DeadDriver()

            with self.assertRaisesRegex(RuntimeError, "invalid session id"):
                scraper.click_subject("CS")

    def test_small_incomplete_scrape_recovers_only_missing_subjects(self):
        class ImmediateFuture:
            def result(self):
                return 1

        class PartialExecutor:
            def __init__(self, max_workers):
                self.max_workers = max_workers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def submit(
                self,
                function,
                subjects,
                term,
                scrape_subdir,
                headless,
                restart_interval,
            ):
                worker_dir = Path(scrape_subdir)
                worker_dir.mkdir(parents=True, exist_ok=True)
                (worker_dir / "Course_Schedule_202690_CS_202691_1200.csv").write_text(
                    "header\n",
                    encoding="utf-8",
                )
                return ImmediateFuture()

        def recover(scraper, subjects, term, delay, restart_interval):
            self.assertEqual(subjects, ["MATH"])
            self.assertEqual(restart_interval, 0)
            (scraper.download_dir / "Course_Schedule_202690_MATH_202691_1201.csv").write_text(
                "header\n",
                encoding="utf-8",
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            updater = ScheduleUpdater(
                scrape_dir=str(root / "scrape"),
                catalog_dir=str(root / "catalog"),
                workers=1,
            )
            updater.RECOVERY_COOLDOWN_SECONDS = 0

            with (
                patch.object(updater, "_get_all_subjects", return_value=["CS", "MATH"]),
                patch("auto_update_scheduler.ProcessPoolExecutor", PartialExecutor),
                patch("auto_update_scheduler.as_completed", side_effect=lambda futures: list(futures)),
                patch.object(NJITSeleniumScraper, "scrape_subject_list", new=recover),
            ):
                self.assertTrue(updater.scrape_latest_data())


if __name__ == "__main__":
    unittest.main()
