"""Tests for the CDN catalog asset builder."""

import csv
import json
import subprocess
import sys
from pathlib import Path


def _write_fixture_csv(path: Path) -> None:
    fieldnames = [
        "Term",
        "Course",
        "Title",
        "Section",
        "CRN",
        "Days",
        "Times",
        "Location",
        "Status",
        "Max",
        "Now",
        "Instructor",
        "Delivery Mode",
        "Credits",
        "Info",
        "Comments",
    ]
    rows = [
        {
            "Course": "CS 100",
            "Title": "Roadmap to Computing",
            "Section": "001",
            "CRN": "10001",
            "Status": "Open",
            "Instructor": "Ada Lovelace",
            "Delivery Mode": "Face-to-Face",
            "Credits": "3",
        },
        {
            "Course": "CS100",
            "Title": "Roadmap to Computing",
            "Section": "002",
            "CRN": "10002",
            "Status": "Closed",
            "Instructor": "Grace Hopper",
            "Delivery Mode": "Online",
            "Credits": "3",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_catalog_assets_are_compact_complete_and_deterministic(tmp_path):
    catalog_dir = tmp_path / "catalog"
    output_dir = tmp_path / "output"
    catalog_dir.mkdir()
    _write_fixture_csv(catalog_dir / "cs.csv")
    script = Path(__file__).parents[2] / "scripts" / "build_catalog_assets.py"

    command = [
        sys.executable,
        str(script),
        "--catalog-dir",
        str(catalog_dir),
        "--output-dir",
        str(output_dir),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    first_index = (output_dir / "index.json").read_text(encoding="utf-8")
    subprocess.run(command, check=True, capture_output=True, text=True)

    index = json.loads(first_index)
    subject = json.loads((output_dir / "subjects" / "CS.json").read_text())
    assert first_index == (output_dir / "index.json").read_text(encoding="utf-8")
    assert index["total"] == 1
    assert index["courses"][0]["section_count"] == 2
    assert index["courses"][0]["open_section_count"] == 1
    assert "sections" not in index["courses"][0]
    assert {section["status"] for section in subject["courses"][0]["sections"]} == {
        "Open",
        "Closed",
    }
