import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from njit_selenium_scraper import NJITSeleniumScraper
from selenium.common.exceptions import NoSuchElementException


class TermSelectionTests(unittest.TestCase):
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
            dropdown.select_by_value.side_effect = NoSuchElementException("missing term")
            with patch("njit_selenium_scraper.Select", return_value=dropdown):
                with self.assertRaises(NoSuchElementException):
                    scraper.select_term("202690")
            dropdown.select_by_value.assert_called_once_with("202690")

    def test_omitted_term_preserves_default(self):
        with tempfile.TemporaryDirectory() as directory:
            scraper = NJITSeleniumScraper(download_dir=directory, headless=True)
            scraper.driver = MagicMock()
            dropdown = MagicMock()
            with patch("njit_selenium_scraper.Select", return_value=dropdown), patch("njit_selenium_scraper.time.sleep"):
                scraper.select_term()
            dropdown.select_by_value.assert_not_called()


if __name__ == "__main__":
    unittest.main()
