import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from njit_selenium_scraper import NJITSeleniumScraper
from selenium.common.exceptions import TimeoutException


class ImmediateWait:
    def __init__(self, driver, timeout):
        self.driver = driver

    def until(self, predicate):
        for _ in range(3):
            value = predicate(self.driver)
            if value:
                return value
        raise TimeoutException('condition not ready')


class TermSelectionTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('njit_selenium_scraper.WebDriverWait', ImmediateWait)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_explicit_term_accepts_plain_and_angular_values(self):
        for value in ("202690", "string:202690"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
                scraper.driver = MagicMock()
                dropdown = MagicMock()
                option = MagicMock()
                option.get_attribute.return_value = value
                dropdown.options = [option]
                with patch("njit_selenium_scraper.Select", return_value=dropdown), patch("njit_selenium_scraper.time.sleep"):
                    scraper.select_term("202690")
                dropdown.select_by_value.assert_called_once_with(value)

    def test_missing_term_raises_instead_of_using_default(self):
        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
            scraper.driver = MagicMock()
            dropdown = MagicMock()
            option = MagicMock()
            option.get_attribute.return_value = "string:202695"
            dropdown.options = [option]
            with patch("njit_selenium_scraper.Select", return_value=dropdown):
                with self.assertRaises(TimeoutException):
                    scraper.select_term("202690")
            dropdown.select_by_value.assert_not_called()

    def test_omitted_term_preserves_default(self):
        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
            scraper.driver = MagicMock()
            dropdown = MagicMock()
            with patch("njit_selenium_scraper.Select", return_value=dropdown), patch("njit_selenium_scraper.time.sleep"):
                scraper.select_term()
            dropdown.select_by_value.assert_not_called()

    def test_subject_list_waits_for_rows_instead_of_accepting_empty_table(self):
        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
            scraper.driver = MagicMock()
            table = scraper.driver.find_element.return_value
            link = MagicMock()
            link.text = 'CS'
            table.find_elements.side_effect = [[], [], [link]]
            self.assertEqual(scraper.get_subjects(), ['CS'])


if __name__ == "__main__":
    unittest.main()
