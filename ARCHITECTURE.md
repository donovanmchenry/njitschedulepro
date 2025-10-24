# NJIT Schedule Pro - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Next.js Frontend                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │   Course     │  │ Availability │  │   Filters    │    │ │
│  │  │   Selector   │  │    Editor    │  │    Panel     │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  │  ┌──────────────┐  ┌──────────────┐                       │ │
│  │  │   Schedule   │  │   Schedule   │                       │ │
│  │  │     View     │  │     List     │                       │ │
│  │  └──────────────┘  └──────────────┘                       │ │
│  │         │                  │                               │ │
│  │         └──────────┬───────┘                               │ │
│  │                    │                                       │ │
│  │         ┌──────────▼─────────┐                            │ │
│  │         │   Zustand Store    │                            │ │
│  │         └────────────────────┘                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                      │
│                    HTTP/JSON API                                │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │               │
┌───────────────────▼───────────────▼──────────────────────────────┐
│                    FastAPI Backend                               │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      API Endpoints                          │  │
│  │  /catalog  /solve  /ingest/csv  /export/ics  /export/csv  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            │                                      │
│  ┌─────────────┬───────────┼───────────┬───────────────────────┐│
│  │             │            │           │                       ││
│  │  ┌──────────▼────┐  ┌───▼──────┐  ┌▼────────────┐  ┌──────▼▼─┐│
│  │  │  Normalizer   │  │  Solver  │  │ ICS Export  │  │ Models ││
│  │  │               │  │          │  │             │  │        ││
│  │  │ • Parse CSV  │  │ • Back-  │  │ • Generate  │  │ • Data ││
│  │  │ • Extract    │  │   track  │  │   iCalendar │  │   types││
│  │  │   days/times │  │ • Filter │  │ • Recur     │  │ • Valid││
│  │  │ • Normalize  │  │ • Score  │  │   rules     │  │   -ation││
│  │  │   data       │  │ • Rank   │  │             │  │        ││
│  │  └───────────────┘  └──────────┘  └─────────────┘  └────────┘│
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                      │
│                   ┌────────▼────────┐                            │
│                   │  In-Memory      │                            │
│                   │  Catalog Store  │                            │
│                   └─────────────────┘                            │
└───────────────────────────────────────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  CSV Files     │
                    │  courseschedules/│
                    └────────────────┘
```

## Data Flow

### 1. Application Startup

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│              │      │              │      │              │
│   Docker     ├─────►│   FastAPI    ├─────►│  Load CSVs   │
│   Compose    │      │   Startup    │      │  from folder │
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                    │
                                            ┌───────▼────────┐
                                            │   Normalize    │
                                            │   all files    │
                                            └───────┬────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  Build catalog │
                                            │   in memory    │
                                            └────────────────┘
```

### 2. Schedule Generation Flow

```
┌──────────────┐
│     User     │
│   selects    │
│   courses    │
└──────┬───────┘
       │
┌──────▼───────┐
│     User     │
│  sets avail  │
│  constraints │
└──────┬───────┘
       │
┌──────▼───────┐      ┌──────────────┐      ┌──────────────┐
│   Click      │      │              │      │              │
│  "Generate   ├─────►│  POST /solve ├─────►│  Validate    │
│  Schedules"  │      │   request    │      │   request    │
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  Pre-filter    │
                                            │  offerings by  │
                                            │  status, etc.  │
                                            └───────┬────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │   Order by     │
                                            │ fewest options │
                                            └───────┬────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  Backtracking  │
                                            │    solver      │
                                            │  • Try section │
                                            │  • Check OK    │
                                            │  • Recurse     │
                                            │  • Backtrack   │
                                            └───────┬────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  Score & rank  │
                                            │   schedules    │
                                            └───────┬────────┘
                                                    │
┌──────────────┐      ┌──────────────┐      ┌─────▼────────┐
│              │      │              │      │              │
│  Display in  │◄─────┤ Return JSON  │◄─────┤ Top N result │
│  calendar    │      │  schedules   │      │   schedules  │
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
```

### 3. Solver Algorithm Detail

```
solve(courses, constraints):
  │
  ├─► Group offerings by course_key
  │
  ├─► Pre-filter:
  │   ├─ Status (Open/Closed/Waitlist)
  │   ├─ Delivery mode
  │   ├─ Instructors
  │   └─ Campus/location
  │
  ├─► Order courses by fewest valid sections
  │
  └─► Backtrack(course_idx=0, current_schedule=[]):
      │
      ├─ BASE CASE: All courses scheduled?
      │  ├─ Check credits in range
      │  ├─ Check not duplicate
      │  ├─ Compute violations
      │  ├─ If violations <= cap: add to results
      │  └─ Return
      │
      └─ RECURSIVE CASE: For each section of current course:
         ├─ Check conflicts with current schedule
         │  └─ If overlaps: skip this section
         │
         ├─ Check availability violations
         │  └─ If exceeds cap: skip this section
         │
         ├─ Add section to schedule
         ├─ Recurse to next course
         └─ Remove section (backtrack)
```

## Component Architecture

### Backend Module Dependencies

```
main.py
  ├─► models.py (data structures)
  ├─► normalizer.py
  │   └─► models.py
  ├─► solver.py
  │   └─► models.py
  └─► ics_export.py
      └─► models.py
```

### Frontend Component Tree

```
page.tsx
  └─► ScheduleBuilder
      ├─► CourseSelector
      │   └─► useAppStore (courses, selectedCourseKeys)
      │
      ├─► AvailabilityEditor
      │   └─► useAppStore (unavailableBlocks, tolerance)
      │
      ├─► FiltersPanel
      │   └─► useAppStore (filters, credits)
      │
      ├─► ScheduleView (if schedules exist)
      │   ├─► useAppStore (schedules, selectedScheduleIndex)
      │   └─► Calendar grid rendering
      │
      └─► ScheduleList (if schedules exist)
          └─► useAppStore (schedules, setSelectedScheduleIndex)
```

## Data Models

### Core Types

```typescript
// Frontend/Backend shared schema

Meeting
  ├─ day: DayOfWeek
  ├─ start_min: number (0-1439)
  ├─ end_min: number (0-1439)
  └─ location?: string

Offering
  ├─ crn: string (unique)
  ├─ course_key: string (e.g., "CS 100")
  ├─ section: string
  ├─ title: string
  ├─ meetings: Meeting[]
  ├─ status: Status (Open/Closed/Waitlist)
  ├─ capacity?: number
  ├─ enrolled?: number
  ├─ instructor?: string
  ├─ delivery: DeliveryMode
  └─ credits?: number

Schedule
  ├─ offerings: Offering[]
  ├─ total_credits: number
  ├─ violations: ScheduleViolation[]
  ├─ total_violation_minutes: number
  ├─ score: number
  └─ is_near_miss: boolean
```

## Performance Characteristics

### Time Complexity

- **CSV Parsing**: O(n) where n = number of rows
- **Solver**: O(b^d) worst case where:
  - b = average sections per course
  - d = number of courses
- **Pruning Optimizations**:
  - Pre-filtering reduces b significantly
  - Fail-fast ordering reduces d effectively
  - Conflict checking is O(m) where m = meetings

### Space Complexity

- **Catalog**: O(n) offerings in memory
- **Solver**: O(d) stack depth for backtracking
- **Results**: O(k) where k = max_results (default 500)

### Scalability Considerations

Current implementation handles:
- 75+ CSV files (one per subject)
- ~5000 total course sections
- Generation of 500+ schedules in < 5 seconds

For larger datasets:
- Add database indexing
- Implement caching layers
- Consider ILP/MIP solvers for optimization
- Paginate results

## Security Considerations

1. **Input Validation**
   - Pydantic models validate all inputs
   - CSV parsing catches malformed data
   - CORS restricted to known origins

2. **File Upload**
   - Currently trusts CSV format
   - Production: validate file types, scan for malicious content
   - Limit file sizes

3. **Rate Limiting**
   - Not implemented (add for production)
   - Prevent solver abuse

4. **Authentication**
   - Currently none (public access)
   - Add OAuth/JWT for user accounts

## Deployment Architecture

### Docker Compose

```
┌─────────────────────────────────────┐
│         Docker Host                 │
│                                     │
│  ┌───────────────┐  ┌────────────┐ │
│  │  web:3000     │  │ api:8000   │ │
│  │  (Next.js)    │◄─┤ (FastAPI)  │ │
│  └───────┬───────┘  └─────┬──────┘ │
│          │                │        │
│  ┌───────▼────────────────▼──────┐ │
│  │    Docker Network             │ │
│  └───────────────────────────────┘ │
│                │                    │
│  ┌─────────────▼──────────────────┐│
│  │   Volume: courseschedules/     ││
│  └────────────────────────────────┘│
└─────────────────────────────────────┘
```

### Production Deployment Options

1. **Single VPS**
   - Docker Compose on DigitalOcean/AWS EC2
   - Nginx reverse proxy
   - SSL with Let's Encrypt

2. **Kubernetes**
   - Separate deployments for API and web
   - Horizontal pod autoscaling
   - Persistent volume for CSVs

3. **Serverless**
   - Vercel for Next.js frontend
   - AWS Lambda + API Gateway for backend
   - S3 for CSV storage

## Monitoring & Observability

### Logging
- FastAPI: uvicorn access logs
- Next.js: console logs
- Production: structured logging (JSON)

### Metrics (To Add)
- Schedule generation time
- Number of results per query
- API response times
- Error rates

### Tracing (To Add)
- OpenTelemetry for distributed tracing
- Track request flow through solver

---

## Future Architectural Improvements

1. **Caching Layer**: Redis for catalog/results
2. **Database**: PostgreSQL with full-text search
3. **Message Queue**: Celery for async solving
4. **CDN**: Static assets on CloudFront/Cloudflare
5. **Microservices**: Split solver into separate service
6. **GraphQL**: Alternative to REST for flexible queries
7. **WebSockets**: Real-time schedule updates
