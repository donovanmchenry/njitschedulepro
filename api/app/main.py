"""FastAPI main application."""

import glob
import os
import re
import time as _time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import httpx
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.ai_parser import AIParseRequest, parse_natural_language
from app.ics_export import generate_ics
from app.models import Offering, Schedule, SolveRequest, SolveResponse
from app.normalizer import normalize_csv, normalize_multiple_csvs
from app.rate_limiter import check_rate_limit, get_global_stats, get_usage_stats, increment_usage
from app.rmp import batch_fetch_ratings
from app.solver import solve_schedules

app = FastAPI(
    title="NJIT Schedule Pro API",
    description="Backend API for course schedule generation",
    version="1.0.0",
)

# CORS middleware for frontend access
default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in allowed_origins_env.split(",")
        if origin.strip()
    ]
    # Always include local development defaults
    allowed_origins.extend(default_origins)
else:
    allowed_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory catalog storage (can be replaced with database)
catalog: List[Offering] = []
catalog_metadata: Dict = {}

# Shared schedules: id → serialized Schedule dict
_shared_schedules: Dict[str, dict] = {}

# Prerequisites cache: normalized course_key → prereq text or None
_prereqs_cache: Dict[str, Optional[str]] = {}

# Solve endpoint rate limiting (separate from AI rate limiter)
# Note: request.client.host is the proxy IP when behind a reverse proxy (e.g. Render).
_solve_rate_limit: Dict[str, List[float]] = {}
SOLVE_RATE_LIMIT = 30  # requests per minute per IP
SOLVE_RATE_WINDOW = 60  # seconds


def _check_solve_rate_limit(ip: str) -> bool:
    """Returns True if the request should be allowed."""
    now = _time.time()
    window_start = now - SOLVE_RATE_WINDOW
    timestamps = [t for t in _solve_rate_limit.get(ip, []) if t > window_start]
    if len(timestamps) >= SOLVE_RATE_LIMIT:
        _solve_rate_limit[ip] = timestamps
        return False
    timestamps.append(now)
    _solve_rate_limit[ip] = timestamps
    return True


class RatingsRequest(BaseModel):
    names: List[str]


def _get_courseschedules_dir() -> str:
    """Resolve the courseschedules directory, checking the mounted volume path first."""
    # Docker volume mounts courseschedules to /app/courseschedules
    volume_path = "/app/courseschedules"
    if os.path.exists(volume_path):
        return volume_path
    # Fallback: parent of cwd (when running from api/ locally)
    parent_dir = os.path.dirname(os.getcwd())
    parent_path = os.path.join(parent_dir, "courseschedules")
    if os.path.exists(parent_path):
        return parent_path
    return os.path.join(os.getcwd(), "courseschedules")


def _load_catalog_from_disk() -> tuple[List[Offering], Dict]:
    """Read all CSVs from the courseschedules directory and return offerings + metadata."""
    courseschedules_dir = _get_courseschedules_dir()
    if not os.path.exists(courseschedules_dir):
        return [], {}
    csv_files = glob.glob(os.path.join(courseschedules_dir, "*.csv"))
    if not csv_files:
        return [], {}
    print(f"Loading {len(csv_files)} CSV files from {courseschedules_dir}...")
    offerings = normalize_multiple_csvs(csv_files)
    metadata = {
        "loaded_at": datetime.now().isoformat(),
        "file_count": len(csv_files),
        "offering_count": len(offerings),
    }
    print(f"Loaded {len(offerings)} offerings from {len(csv_files)} files")
    return offerings, metadata


@app.on_event("startup")
async def startup_event():
    """Load existing CSVs from courseschedules directory on startup."""
    global catalog, catalog_metadata
    catalog, catalog_metadata = _load_catalog_from_disk()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "NJIT Schedule Pro API",
        "version": "1.0.0",
        "catalog_loaded": len(catalog) > 0,
        "catalog_size": len(catalog),
    }


@app.post("/reload")
async def reload_catalog(x_reload_secret: Optional[str] = Header(default=None)):
    """
    Reload the course catalog from disk without restarting the server.
    If the RELOAD_SECRET env var is set, the X-Reload-Secret header must match it.
    """
    global catalog, catalog_metadata

    reload_secret = os.getenv("RELOAD_SECRET")
    if reload_secret and x_reload_secret != reload_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Reload-Secret header")

    catalog, catalog_metadata = _load_catalog_from_disk()
    return {
        "status": "reloaded",
        "offering_count": len(catalog),
        "loaded_at": catalog_metadata.get("loaded_at"),
    }


@app.post("/ingest/csv")
async def ingest_csv(file: UploadFile = File(...)):
    """
    Ingest a single CSV file and add to catalog.

    Args:
        file: CSV file upload

    Returns:
        Status and updated catalog info
    """
    global catalog, catalog_metadata

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Save temporarily
        temp_path = f"/tmp/{file.filename}"
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)

        # Normalize
        new_offerings = normalize_csv(temp_path)

        # Add to catalog (with deduplication by CRN)
        existing_crns = {o.crn for o in catalog}
        added = 0
        for offering in new_offerings:
            if offering.crn not in existing_crns:
                catalog.append(offering)
                existing_crns.add(offering.crn)
                added += 1

        catalog_metadata = {
            "updated_at": datetime.now().isoformat(),
            "offering_count": len(catalog),
        }

        # Clean up
        os.remove(temp_path)

        return {
            "status": "success",
            "filename": file.filename,
            "new_offerings": len(new_offerings),
            "added_to_catalog": added,
            "total_catalog_size": len(catalog),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.get("/catalog")
async def get_catalog(
    course_key: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get catalog of offerings with optional filtering.

    Args:
        course_key: Filter by specific course key (e.g., 'CS 100')
        search: Search in course key or title
        limit: Max results to return
        offset: Pagination offset

    Returns:
        List of offerings and metadata
    """
    filtered = catalog

    if course_key:
        filtered = [o for o in filtered if o.course_key.lower() == course_key.lower()]

    if search:
        search_lower = search.lower()
        filtered = [
            o
            for o in filtered
            if search_lower in o.course_key.lower() or search_lower in o.title.lower()
        ]

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    # Get unique course keys for frontend
    unique_courses = {}
    for offering in catalog:
        if offering.course_key not in unique_courses:
            unique_courses[offering.course_key] = {
                "course_key": offering.course_key,
                "title": offering.title,
                "section_count": 0,
            }
        unique_courses[offering.course_key]["section_count"] += 1

    return {
        "offerings": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "unique_courses": list(unique_courses.values()),
        "metadata": catalog_metadata,
    }


@app.get("/catalog/courses")
async def get_courses(search: Optional[str] = None):
    """
    Get list of unique courses with section counts.

    Args:
        search: Optional search filter

    Returns:
        List of courses
    """
    course_map = {}

    for offering in catalog:
        if offering.course_key not in course_map:
            course_map[offering.course_key] = {
                "course_key": offering.course_key,
                "title": offering.title,
                "sections": {},  # Changed to dict to group by CRN
            }

        # Group sections by CRN to avoid duplicates
        crn = offering.crn
        if crn not in course_map[offering.course_key]["sections"]:
            course_map[offering.course_key]["sections"][crn] = {
                "crn": offering.crn,
                "section": offering.section,
                "status": offering.status.value,
                "delivery": offering.delivery.value,
                "instructor": offering.instructor,
                "credits": offering.credits,
            }

    # Convert sections dict back to list
    courses = []
    for course_data in course_map.values():
        course_data["sections"] = list(course_data["sections"].values())
        courses.append(course_data)

    if search:
        search_lower = search.lower()
        courses = [
            c
            for c in courses
            if search_lower in c["course_key"].lower() or search_lower in c["title"].lower()
        ]

    return {"courses": courses, "total": len(courses)}


@app.post("/solve", response_model=SolveResponse)
async def solve(request_body: SolveRequest, request: Request):
    """
    Generate schedules based on constraints.

    Args:
        request_body: Solve request with constraints
        request: FastAPI request object (for rate limiting)

    Returns:
        List of valid schedules
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_solve_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many schedule requests. Limit is 30 per minute. Please wait and try again.",
        )

    if not catalog:
        raise HTTPException(status_code=400, detail="Catalog is empty. Please ingest CSV files first.")

    # Validate required courses exist
    catalog_course_keys = {o.course_key for o in catalog}
    missing = [ck for ck in request_body.required_course_keys if ck not in catalog_course_keys]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Required courses not found in catalog: {', '.join(missing)}"
        )

    # Solve
    schedules = solve_schedules(catalog, request_body)

    # Count unique courses in catalog
    unique_courses = len(set(o.course_key for o in catalog))

    return SolveResponse(
        schedules=schedules,
        count=len(schedules),
        catalog_course_count=unique_courses,
        catalog_section_count=len(catalog),
    )


@app.post("/ai/parse-schedule")
async def ai_parse_schedule(parse_request: AIParseRequest, request: Request):
    """
    Parse natural language schedule description into structured constraints using AI.

    Args:
        parse_request: Contains user prompt and optional API key
        request: FastAPI request object (for IP address)

    Returns:
        Parsed constraints and usage information
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Check if user is providing their own API key
    use_user_key = parse_request.user_api_key is not None

    # Check rate limits (skip if using own key)
    allowed, error_msg = check_rate_limit(client_ip, use_user_key)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        # Parse using AI
        result = await parse_natural_language(
            parse_request.prompt, parse_request.user_api_key
        )

        # Increment usage counter
        increment_usage(client_ip, use_user_key)

        # Get updated usage stats
        usage_stats = get_usage_stats(client_ip)

        return {
            "success": True,
            "constraints": result.constraints.model_dump(),
            "confidence": result.confidence,
            "usage": usage_stats,
        }

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error parsing schedule: {str(e)}"
        )


@app.get("/ai/usage")
async def get_ai_usage(request: Request):
    """
    Get AI usage statistics for the current user.

    Args:
        request: FastAPI request object (for IP address)

    Returns:
        Usage statistics
    """
    client_ip = request.client.host if request.client else "unknown"
    return get_usage_stats(client_ip)


@app.get("/ai/global-stats")
async def get_ai_global_stats():
    """
    Get global AI usage statistics (admin endpoint).

    Returns:
        Global usage statistics
    """
    return get_global_stats()


@app.post("/export/ics")
async def export_ics(
    schedule: Schedule,
    term_start: str = "2026-09-01",  # Default Fall 2026 start
    term_end: str = "2026-12-13",  # Default Fall 2026 end (last day of classes)
):
    """
    Export a schedule as an ICS calendar file.

    Args:
        schedule: Schedule to export
        term_start: Term start date (YYYY-MM-DD)
        term_end: Term end date (YYYY-MM-DD)

    Returns:
        ICS file download
    """
    try:
        start_date = datetime.strptime(term_start, "%Y-%m-%d")
        end_date = datetime.strptime(term_end, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    ics_bytes = generate_ics(schedule, start_date, end_date)

    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=njit_schedule.ics"},
    )


def _minutes_to_ampm(total_minutes: int) -> str:
    """Convert minutes-from-midnight to 12-hour AM/PM string (e.g. 780 → '1:00 PM')."""
    h = total_minutes // 60
    m = total_minutes % 60
    period = "PM" if h >= 12 else "AM"
    display_h = h % 12 or 12
    return f"{display_h}:{m:02d} {period}"


@app.post("/export/csv")
async def export_csv(schedule: Schedule):
    """
    Export a schedule as a CSV file.

    Args:
        schedule: Schedule to export

    Returns:
        CSV file download
    """
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Course",
            "Title",
            "CRN",
            "Section",
            "Days",
            "Times",
            "Location",
            "Instructor",
            "Delivery",
            "Credits",
            "Status",
        ]
    )

    # Rows
    for offering in schedule.offerings:
        # Format days and times
        if offering.meetings:
            days_str = "".join(sorted(set(m.day.value[0] for m in offering.meetings)))
            first_meeting = offering.meetings[0]
            times_str = f"{_minutes_to_ampm(first_meeting.start_min)} - {_minutes_to_ampm(first_meeting.end_min)}"
            location = first_meeting.location or ""
        else:
            days_str = "TBA"
            times_str = "TBA"
            location = ""

        writer.writerow(
            [
                offering.course_key,
                offering.title,
                offering.crn,
                offering.section,
                days_str,
                times_str,
                location,
                offering.instructor or "",
                offering.delivery.value,
                offering.credits or "",
                offering.status.value,
            ]
        )

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=njit_schedule.csv"},
    )


@app.post("/professors/ratings")
async def get_professor_ratings(req: RatingsRequest):
    """
    Fetch RateMyProfessor ratings for a list of instructor names.
    Never raises — returns empty dict if RMP is unreachable.
    """
    if not req.names:
        return {}
    valid = [n for n in req.names if n and n.strip() and n != "Staff TBA"]
    if not valid:
        return {}
    try:
        return await batch_fetch_ratings(valid)
    except Exception:
        return {}


@app.get("/catalog/prerequisites/{course_key:path}")
async def get_prerequisites(course_key: str):
    """
    Fetch prerequisites for a course from the NJIT course catalog.
    Scrapes catalog.njit.edu and caches results in memory.
    """
    cache_key = course_key.strip().upper()
    if cache_key in _prereqs_cache:
        return {"prerequisites": _prereqs_cache[cache_key]}

    # Build catalog search URL, e.g. "CS 114" → "?P=CS+114"
    search_term = cache_key.replace(" ", "+")

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(
                f"https://catalog.njit.edu/search/?P={search_term}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                # Find the first "Prerequisite" sentence on the page
                match = re.search(
                    r"Prerequisite[s]?:\s*(.*?)(?:<br|</p|<div)",
                    resp.text,
                    re.IGNORECASE | re.DOTALL,
                )
                if match:
                    raw = match.group(1)
                    # Strip HTML tags and collapse whitespace
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    # Keep only the first sentence (prereq condition);
                    # the catalog appends the course description after it
                    first_sentence = re.split(r"\.\s+[A-Z]", clean)[0].rstrip(" .")
                    prereqs = first_sentence if len(first_sentence) > 3 else None
                    _prereqs_cache[cache_key] = prereqs
                    return {"prerequisites": prereqs}
    except Exception:
        pass

    _prereqs_cache[cache_key] = None
    return {"prerequisites": None}


@app.post("/share")
async def create_share(schedule: Schedule):
    """
    Save a schedule and return a short ID that can be used to retrieve it.
    The schedule is kept in memory; links expire when the server restarts.
    """
    share_id = uuid.uuid4().hex[:8]
    _shared_schedules[share_id] = schedule.model_dump()
    return {"id": share_id}


@app.get("/share/{share_id}")
async def get_share(share_id: str):
    """Retrieve a previously shared schedule by its short ID."""
    data = _shared_schedules.get(share_id)
    if not data:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    return data
