# NJIT Schedule Pro

A production-ready course schedule generator for NJIT students that uses advanced constraint solving to find valid schedules based on course requirements, time availability, and preferences.

## Features

- **Smart Schedule Generation**: Advanced backtracking solver generates all feasible schedules
- **Flexible Constraints**: Set unavailable time blocks, credit limits, and preferences
- **Strict Availability Enforcement**: Ensures no conflicts with unavailable time blocks
- **Rich Filtering**: Filter by course status, delivery mode, instructors, campus, honors classes, and more
- **Interactive Calendar**: Visual weekly calendar view with drag-free course display
- **Multiple Exports**: Download schedules as ICS calendar files or CSV
- **Bookmark Favorites**: Save and compare your favorite schedule options
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile

## Architecture

### Backend (FastAPI + Python)
- **Data Normalization**: Robust CSV parsing with support for various NJIT formats
- **Constraint Solver**: Backtracking algorithm with intelligent pruning
- **RESTful API**: Clean API endpoints for catalog, solving, and export
- **Type Safety**: Full pydantic models for validation

### Frontend (Next.js 14 + TypeScript)
- **Modern Stack**: React 18, TypeScript, Tailwind CSS
- **State Management**: Zustand for efficient global state
- **Responsive UI**: Mobile-first design with shadcn/ui components
- **Real-time Updates**: Instant feedback on schedule generation

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   cd njitschedulepro
   ```

2. **Ensure CSV files are in place**
   The application expects CSV files in the `courseschedules/` directory. The files should follow NJIT's course schedule format.

3. **Start the application**
   ```bash
   docker compose up
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development

#### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm 8+
- Poetry (Python package manager)

#### Backend Setup

1. **Navigate to the API directory**
   ```bash
   cd api
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Run the development server**
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

4. **Run tests**
   ```bash
   poetry run pytest
   ```

#### Frontend Setup

1. **Navigate to the web directory**
   ```bash
   cd web
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Run the development server**
   ```bash
   pnpm dev
   ```

4. **Build for production**
   ```bash
   pnpm build
   pnpm start
   ```

#### Run Both (from root)
```bash
pnpm install
pnpm dev
```

## CSV Format

The application expects CSV files with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| Term | Semester code | `202610` |
| Course | Course code | `CS100` or `CS 100` |
| Title | Course title | `ROADMAP TO COMPUTING` |
| Section | Section number | `002` |
| CRN | Course Reference Number | `11757` |
| Days | Meeting days | `MW`, `TR`, `MWF` |
| Times | Meeting times | `11:30 AM - 12:50 PM` |
| Location | Room/building | `CKB 217` |
| Status | Section status | `Open`, `Closed`, `Waitlist` |
| Max | Max enrollment | `80` |
| Now | Current enrollment | `45` |
| Instructor | Instructor name | `Smith, John` |
| Delivery Mode | Delivery type | `Face-to-Face`, `Online`, `Hybrid` |
| Credits | Credit hours | `3` |
| Info | Additional info | URL or notes |
| Comments | Course comments | Special requirements |

### Day Codes
- `M` = Monday
- `T` = Tuesday
- `W` = Wednesday
- `R` = Thursday (R to avoid confusion with T)
- `F` = Friday
- `S` = Saturday
- `U` = Sunday

## Usage Guide

### 1. Select Courses
- Use the search box to find courses by code (e.g., "CS 100") or title
- Click to add courses to your required list
- Remove courses by clicking the X button

### 2. Set Availability Constraints
- Select days and times when you are **unavailable**
- Add multiple blocks for work, commute, or other commitments
- Schedules will strictly avoid these time blocks

### 3. Configure Filters
- **Status**: Include Open, Waitlist, or Closed sections
- **Credits**: Set minimum and maximum credit limits
- **Max Gap**: Limit breaks between classes on the same day
- **Delivery Mode**: Filter by in-person, online, hybrid, or async
- **Honors Classes**: Toggle honors sections (H prefix) on/off

### 4. Generate Schedules
- Click "Generate Schedules" to run the solver
- View all feasible schedules ranked by quality
- Schedules are sorted by minimal gaps and preferences

### 5. Review & Export
- Browse schedules in the calendar view
- Click schedules in the list to switch between options
- Bookmark favorites for comparison
- Download as ICS (import to Google Calendar) or CSV

## API Endpoints

### `GET /`
Health check and status

### `POST /ingest/csv`
Upload additional CSV files to the catalog
- **Body**: Multipart form with CSV file
- **Returns**: Ingestion status and catalog size

### `GET /catalog`
Retrieve course catalog with optional filtering
- **Query Params**: `course_key`, `search`, `limit`, `offset`
- **Returns**: List of offerings and metadata

### `GET /catalog/courses`
Get unique courses with section counts
- **Query Params**: `search`
- **Returns**: Aggregated course list

### `POST /solve`
Generate schedules based on constraints
- **Body**: `SolveRequest` JSON
- **Returns**: `SolveResponse` with schedules

### `POST /export/ics`
Export schedule as ICS calendar file
- **Body**: `Schedule` JSON + term dates
- **Returns**: Downloadable .ics file

### `POST /export/csv`
Export schedule as CSV
- **Body**: `Schedule` JSON
- **Returns**: Downloadable .csv file

## Algorithm Details

### Constraint Solver

The solver uses **backtracking with intelligent pruning**:

1. **Pre-filtering**: Apply status, delivery, instructor, campus filters
2. **Ordering**: Process courses with fewest valid sections first (fail-fast)
3. **Backtracking**: Recursively try each section for each course
4. **Conflict Detection**: Check for time overlaps between meetings
5. **Availability Check**: Strict validation against unavailable blocks (no tolerance)
6. **Credit Validation**: Ensure total credits meet min/max requirements
7. **Deduplication**: Remove duplicate schedules by CRN signature

### Scoring & Ranking

Schedules are scored (lower is better) based on:

1. **Primary**: Time gaps between classes (heavily weighted)
2. **Secondary**: Instructor preferences
3. **Tertiary**: Open seat availability
4. **Tie-break**: Deterministic by CRN sum

## Project Structure

```
njitschedulepro/
├── api/                      # FastAPI backend
│   ├── app/
│   │   ├── main.py          # FastAPI app and endpoints
│   │   ├── models.py        # Pydantic data models
│   │   ├── normalizer.py    # CSV parsing and normalization
│   │   ├── solver.py        # Constraint solver
│   │   └── ics_export.py    # ICS calendar generation
│   ├── tests/               # Unit tests
│   ├── pyproject.toml       # Python dependencies
│   └── Dockerfile
├── web/                      # Next.js frontend
│   ├── src/
│   │   ├── app/             # Next.js app router
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities and state
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── courseschedules/         # CSV data directory
├── docker-compose.yml       # Docker orchestration
├── package.json             # Monorepo root
└── README.md
```

## Testing

### Backend Tests
```bash
cd api
poetry run pytest
poetry run pytest --cov=app --cov-report=html
```

### Frontend Tests (if implemented)
```bash
cd web
pnpm test
pnpm test:coverage
```

## Deployment

### Production Build
```bash
# Build both services
docker compose build

# Run in production mode
docker compose up -d
```

### Environment Variables

#### API
- `PYTHONUNBUFFERED=1` - Enable Python output buffering

#### Web
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Troubleshooting

### No schedules found
- **Cause**: Constraints are too restrictive
- **Solution**:
  - Remove some availability constraints
  - Include Waitlist/Closed sections
  - Reduce credit requirements
  - Adjust time window filters

### Slow schedule generation
- **Cause**: Large number of sections or complex constraints
- **Solution**:
  - Filter by status (Open only)
  - Reduce max_results parameter
  - Add time window filters (earliest_start, latest_end)

### CSV import errors
- **Cause**: Incorrect format or missing columns
- **Solution**:
  - Verify CSV has all required columns
  - Check date/time formats (e.g., "11:30 AM - 12:50 PM")
  - Ensure day codes are correct (M, T, W, R, F)

## Contributing

### Code Style
- **Python**: Black formatter, Ruff linter
- **TypeScript**: ESLint with Next.js config
- **Commits**: Conventional commits format

### Development Workflow
1. Create feature branch
2. Make changes with tests
3. Run linters and tests
4. Submit pull request

## License

This project is provided as-is for educational purposes.

## Acknowledgments

- NJIT for course schedule data
- FastAPI and Next.js communities
- Contributors and testers

## Support

For issues, questions, or contributions, please open an issue on the repository.

---

Built by Donovan McHenry
