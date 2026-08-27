#!/usr/bin/env python3
"""Run adversarial schedule descriptions through the production AI parser."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.ai_parser import parse_natural_language  # noqa: E402

DEFAULT_CASES = API_ROOT / "evals" / "ai_schedule_descriptions.json"
DEFAULT_JSON_REPORT = API_ROOT / "evals" / "latest-results.json"
DEFAULT_MARKDOWN_REPORT = API_ROOT / "evals" / "latest-results.md"


def normalized(value: Any) -> Any:
    """Normalize unordered fields so semantically identical output compares cleanly."""
    if isinstance(value, list):
        normalized_items = [normalized(item) for item in value]
        return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in sorted(value.items())}
    return value


def score_case(case: dict[str, Any], actual: dict[str, Any] | None, error: str | None) -> dict[str, Any]:
    """Score each expected field independently and label exact/partial/fail."""
    if case.get("expected_error"):
        matched = error is not None
        return {
            "verdict": "exact" if matched else "fail",
            "matched_fields": ["expected_error"] if matched else [],
            "failed_fields": [] if matched else ["expected_error"],
            "field_details": {},
        }

    expected = case["expected"]
    if error is not None or actual is None:
        return {
            "verdict": "fail",
            "matched_fields": [],
            "failed_fields": list(expected) + (["confidence"] if "expected_confidence" in case else []),
            "field_details": {"error": error},
        }

    matched_fields: list[str] = []
    failed_fields: list[str] = []
    field_details: dict[str, Any] = {}

    for field, expected_value in expected.items():
        actual_value = actual.get(field)
        if normalized(actual_value) == normalized(expected_value):
            matched_fields.append(field)
        else:
            failed_fields.append(field)
            field_details[field] = {"expected": expected_value, "actual": actual_value}

    if "expected_confidence" in case:
        expected_confidence = case["expected_confidence"]
        actual_confidence = actual.get("confidence")
        if actual_confidence == expected_confidence:
            matched_fields.append("confidence")
        else:
            failed_fields.append("confidence")
            field_details["confidence"] = {
                "expected": expected_confidence,
                "actual": actual_confidence,
            }

    if not failed_fields:
        verdict = "exact"
    elif matched_fields:
        verdict = "partial"
    else:
        verdict = "fail"

    return {
        "verdict": verdict,
        "matched_fields": matched_fields,
        "failed_fields": failed_fields,
        "field_details": field_details,
    }


async def evaluate_case(case: dict[str, Any], semaphore: asyncio.Semaphore) -> dict[str, Any]:
    """Call the same model and validation path used by the API endpoint."""
    actual: dict[str, Any] | None = None
    error: str | None = None

    async with semaphore:
        started = time.perf_counter()
        try:
            parsed = await parse_natural_language(case["prompt"])
            actual = parsed.constraints.model_dump(mode="json")
            actual["course_requirements"] = [
                {
                    "departments": group.departments,
                    "minimum_level": group.minimum_level,
                    "course_count": group.choose,
                }
                for group in parsed.constraints.course_groups
                if group.requirement_id is None
            ]
            actual["named_requirements"] = [
                "Computing Literacy GER"
                for group in parsed.constraints.course_groups
                if group.requirement_id == "computing_literacy_ger"
            ]
            actual["confidence"] = parsed.confidence
        except Exception as exc:  # The report must retain provider and validation failures.
            error = f"{type(exc).__name__}: {exc}"
        duration_ms = round((time.perf_counter() - started) * 1000)

    score = score_case(case, actual, error)
    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "catalog_basis": case["catalog_basis"],
        "expected": case.get("expected"),
        "expected_confidence": case.get("expected_confidence"),
        "expected_error": case.get("expected_error", False),
        "actual": actual,
        "error": error,
        "duration_ms": duration_ms,
        **score,
    }


def markdown_report(report: dict[str, Any]) -> str:
    """Create a compact, reviewable report with every field mismatch."""
    summary = report["summary"]
    lines = [
        "# AI schedule description evaluation",
        "",
        f"Run: {report['run_at']}",
        f"Model: `{report['model']}`",
        f"Cases: {summary['total']} · Exact: {summary['exact']} · Partial: {summary['partial']} · Fail: {summary['fail']}",
        f"Exact rate: {summary['exact_rate']}% · Median latency: {summary['median_duration_ms']} ms",
        "",
        "| Case | Result | Time | Failed fields |",
        "| --- | --- | ---: | --- |",
    ]

    for result in report["results"]:
        failed = ", ".join(result["failed_fields"]) or "—"
        lines.append(
            f"| `{result['id']}` | {result['verdict']} | {result['duration_ms']} ms | {failed} |"
        )

    lines.extend(["", "## Mismatches", ""])
    mismatches = [result for result in report["results"] if result["verdict"] != "exact"]
    if not mismatches:
        lines.append("None.")
    else:
        for result in mismatches:
            lines.extend(
                [
                    f"### {result['id']}",
                    "",
                    f"> {result['prompt']}",
                    "",
                ]
            )
            if result["error"]:
                lines.append(f"Error: `{result['error']}`")
                lines.append("")
            for field, detail in result["field_details"].items():
                if isinstance(detail, dict):
                    lines.append(
                        f"- `{field}` expected `{json.dumps(detail.get('expected'))}`, "
                        f"got `{json.dumps(detail.get('actual'))}`"
                    )
            lines.append("")

    lines.extend(["## Failure frequency", ""])
    for field, count in summary["failed_field_counts"].items():
        lines.append(f"- `{field}`: {count}")
    if not summary["failed_field_counts"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown-report", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--ids", nargs="*", help="Run only the named case IDs")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        parser.error("ANTHROPIC_API_KEY is required")
    if args.concurrency < 1 or args.concurrency > 10:
        parser.error("--concurrency must be between 1 and 10")

    cases = json.loads(args.cases.read_text())
    if args.ids:
        selected_ids = set(args.ids)
        cases = [case for case in cases if case["id"] in selected_ids]
        missing_ids = selected_ids - {case["id"] for case in cases}
        if missing_ids:
            parser.error(f"Unknown case IDs: {', '.join(sorted(missing_ids))}")
    semaphore = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*(evaluate_case(case, semaphore) for case in cases))

    verdict_counts = Counter(result["verdict"] for result in results)
    failed_field_counts: Counter[str] = Counter()
    for result in results:
        failed_field_counts.update(result["failed_fields"])

    total = len(results)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "summary": {
            "total": total,
            "exact": verdict_counts["exact"],
            "partial": verdict_counts["partial"],
            "fail": verdict_counts["fail"],
            "exact_rate": round(verdict_counts["exact"] / total * 100, 1),
            "median_duration_ms": round(statistics.median(result["duration_ms"] for result in results)),
            "failed_field_counts": dict(sorted(failed_field_counts.items())),
        },
        "results": results,
    }

    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(json.dumps(report, indent=2) + "\n")
    args.markdown_report.write_text(markdown_report(report))

    print(json.dumps(report["summary"], indent=2))
    return 0 if verdict_counts["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
