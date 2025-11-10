"""FastAPI main application."""

import glob
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.ai_parser import AIParseRequest, parse_natural_language
from app.ics_export import generate_ics
from app.models import Offering, Schedule, SolveRequest, SolveResponse
from app.normalizer import normalize_csv, normalize_multiple_csvs
from app.rate_limiter import check_rate_limit, get_global_stats, get_usage_stats, increment_usage
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


@app.on_event("startup")
async def startup_event():
    """Load existing CSVs from courseschedules directory on startup."""
    global catalog, catalog_metadata

    # Look for courseschedules in parent directory (when running from api/)
    parent_dir = os.path.dirname(os.getcwd())
    courseschedules_dir = os.path.join(parent_dir, "courseschedules")
    # Fallback to current directory if not found
    if not os.path.exists(courseschedules_dir):
        courseschedules_dir = os.path.join(os.getcwd(), "courseschedules")
    if os.path.exists(courseschedules_dir):
        csv_files = glob.glob(os.path.join(courseschedules_dir, "*.csv"))
        if csv_files:
            print(f"Loading {len(csv_files)} CSV files from {courseschedules_dir}...")
            catalog = normalize_multiple_csvs(csv_files)
            catalog_metadata = {
                "loaded_at": datetime.now().isoformat(),
                "file_count": len(csv_files),
                "offering_count": len(catalog),
            }
            print(f"Loaded {len(catalog)} offerings from {len(csv_files)} files")


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
async def solve(request: SolveRequest):
    """
    Generate schedules based on constraints.

    Args:
        request: Solve request with constraints

    Returns:
        List of valid schedules
    """
    if not catalog:
        raise HTTPException(status_code=400, detail="Catalog is empty. Please ingest CSV files first.")

    # Validate required courses exist
    catalog_course_keys = {o.course_key for o in catalog}
    missing = [ck for ck in request.required_course_keys if ck not in catalog_course_keys]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Required courses not found in catalog: {', '.join(missing)}"
        )

    # Solve
    schedules = solve_schedules(catalog, request)

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
    term_start: str = "2026-01-21",  # Default Spring 2026 start
    term_end: str = "2026-05-08",  # Default Spring 2026 end
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
            start_hr = first_meeting.start_min // 60
            start_min = first_meeting.start_min % 60
            end_hr = first_meeting.end_min // 60
            end_min = first_meeting.end_min % 60
            times_str = f"{start_hr:02d}:{start_min:02d} - {end_hr:02d}:{end_min:02d}"
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
