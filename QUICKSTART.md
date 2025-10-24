# Quick Start Guide

## Option 1: Docker (Easiest)

1. **Start the application**
   ```bash
   docker compose up
   ```

2. **Access**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

The application will automatically load all CSV files from the `courseschedules/` directory on startup.

## Option 2: Local Development

### Backend
```bash
cd api
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend (in a new terminal)
```bash
cd web
pnpm install
pnpm dev
```

Access at http://localhost:3000

## First Time Setup

### Install Dependencies

**If using Docker:** Just run `docker compose up`

**If using local development:**

1. **Install Poetry (Python package manager)**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install pnpm (Node package manager)**
   ```bash
   npm install -g pnpm
   ```

3. **Install API dependencies**
   ```bash
   cd api
   poetry install
   ```

4. **Install Web dependencies**
   ```bash
   cd web
   pnpm install
   ```

## Using the Application

1. **Select Courses**
   - Search for courses (e.g., "CS 100", "Math", etc.)
   - Click to add to your schedule

2. **Set Availability**
   - Add time blocks when you're unavailable
   - Adjust near-miss tolerance if you want flexible scheduling

3. **Configure Filters**
   - Choose section status (Open, Waitlist, Closed)
   - Set credit limits
   - Filter by delivery mode

4. **Generate Schedules**
   - Click "Generate Schedules"
   - Browse all valid options
   - View on calendar grid

5. **Export**
   - Download as ICS (for Google Calendar, Outlook, etc.)
   - Download as CSV

## Testing

### Test Backend
```bash
cd api
poetry run pytest
```

### View Coverage
```bash
cd api
poetry run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Port already in use
If ports 3000 or 8000 are in use, modify `docker-compose.yml` or run on different ports:

```bash
# Backend
cd api
poetry run uvicorn app.main:app --reload --port 8001

# Frontend
cd web
pnpm dev -p 3001
```

### No courses showing
- Ensure CSV files are in `courseschedules/` directory
- Check API logs for parsing errors
- Verify CSV format matches expected schema (see README.md)

### Module not found errors
- Run `poetry install` in api/ directory
- Run `pnpm install` in web/ directory
- Clear caches: `pnpm store prune` and `poetry cache clear pypi --all`

## Development Tips

### Hot Reload
Both frontend and backend support hot reload:
- Backend: Changes to `app/` auto-reload
- Frontend: Changes to `src/` auto-reload

### API Documentation
Visit http://localhost:8000/docs for interactive API documentation (Swagger UI)

### Debugging
- **Backend**: Add `import pdb; pdb.set_trace()` for breakpoints
- **Frontend**: Use browser DevTools, React DevTools extension

### Code Formatting
```bash
# Backend
cd api
poetry run black app tests
poetry run ruff check app tests

# Frontend
cd web
pnpm lint
```

## Next Steps

See `README.md` for:
- Full API documentation
- Algorithm details
- CSV format specification
- Deployment instructions
- Contributing guidelines

---

Happy scheduling!
