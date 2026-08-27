#!/usr/bin/env python3
"""Build compact, CDN-cacheable course catalog assets from the scraped CSV files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def extract_course_key(value: str) -> str:
    match = re.match(r"([A-Z]+)\s*(\d+)([A-Z]*)", value.strip().upper())
    if not match:
        return value.strip().upper()
    return f"{match.group(1)} {match.group(2)}{match.group(3)}"


def normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if "closed" in normalized:
        return "Closed"
    if "wait" in normalized:
        return "Waitlist"
    return "Open"


def normalize_delivery(value: str, location: str) -> str:
    normalized = value.strip().lower()
    if "async" in normalized:
        return "Async"
    if "hybrid" in normalized or "blended" in normalized:
        return "Hybrid"
    if any(token in normalized for token in ("online", "web", "distance")):
        return "Online"
    if not normalized and any(token in location.lower() for token in ("online", "web")):
        return "Online"
    return "In-Person"


def optional_float(value: str) -> float | None:
    try:
        return float(value) if value.strip() else None
    except (AttributeError, ValueError):
        return None


def build_assets(catalog_dir: Path, output_dir: Path) -> tuple[int, int, str]:
    courses: dict[str, dict] = {}
    for csv_path in sorted(catalog_dir.glob("*.csv")):
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                crn = (row.get("CRN") or "").strip()
                course_key = extract_course_key(row.get("Course") or "")
                if not crn or not course_key:
                    continue
                course = courses.setdefault(
                    course_key,
                    {
                        "course_key": course_key,
                        "title": (row.get("Title") or "").strip(),
                        "subject": course_key.split(" ", 1)[0],
                        "sections": {},
                    },
                )
                course["sections"].setdefault(
                    crn,
                    {
                        "crn": crn,
                        "section": (row.get("Section") or "").strip(),
                        "status": normalize_status(row.get("Status") or ""),
                        "delivery": normalize_delivery(
                            row.get("Delivery Mode") or "",
                            row.get("Location") or "",
                        ),
                        "instructor": (row.get("Instructor") or "").strip() or None,
                        "credits": optional_float(row.get("Credits") or ""),
                    },
                )

    subject_courses: dict[str, list[dict]] = defaultdict(list)
    index_courses: list[dict] = []
    for course_key in sorted(courses):
        course = courses[course_key]
        sections = list(course.pop("sections").values())
        summary = {
            "course_key": course["course_key"],
            "title": course["title"],
            "subject": course["subject"],
            "section_count": len(sections),
            "open_section_count": sum(section["status"] == "Open" for section in sections),
        }
        index_courses.append(summary)
        subject_courses[course["subject"]].append({**summary, "sections": sections})

    digest_source = json.dumps(subject_courses, sort_keys=True, separators=(",", ":")).encode()
    version = hashlib.sha256(digest_source).hexdigest()[:16]

    subjects_dir = output_dir / "subjects"
    subjects_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in subjects_dir.glob("*.json"):
        stale_path.unlink()

    for subject, subject_items in sorted(subject_courses.items()):
        payload = {"version": version, "subject": subject, "courses": subject_items}
        (subjects_dir / f"{subject}.json").write_text(
            json.dumps(payload, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.json").write_text(
        json.dumps(
            {"version": version, "courses": index_courses, "total": len(index_courses)},
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return len(index_courses), len(subject_courses), version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, default=Path("courseschedules"))
    parser.add_argument("--output-dir", type=Path, default=Path("web/public/catalog"))
    args = parser.parse_args()
    course_count, subject_count, version = build_assets(args.catalog_dir, args.output_dir)
    print(
        f"Built catalog {version}: {course_count} courses across {subject_count} subjects"
    )


if __name__ == "__main__":
    main()
