# API Integration for Manual Updates

This guide shows how to add admin endpoints to your API for triggering catalog updates from your web interface.

## Option 1: Quick Integration (Recommended)

Add admin endpoints to your existing API:

### Step 1: Import the Admin Router

Edit `/api/app/main.py` and add this import near the top with your other imports:

```python
from app.admin_endpoints import router as admin_router
```

### Step 2: Include the Router

Add this line after creating your `app` instance but before your endpoints:

```python
# Include admin router
app.include_router(admin_router)
```

### Full Example

Your `main.py` imports should look like:

```python
from app.ai_parser import AIParseRequest, parse_natural_language
from app.ics_export import generate_ics
from app.models import Offering, Schedule, SolveRequest, SolveResponse
from app.normalizer import normalize_csv, normalize_multiple_csvs
from app.rate_limiter import check_rate_limit, get_global_stats, get_usage_stats, increment_usage
from app.solver import solve_schedules
from app.admin_endpoints import router as admin_router  # <-- ADD THIS
```

And after creating the app:

```python
app = FastAPI(
    title="NJIT Schedule Pro API",
    description="Backend API for course schedule generation",
    version="1.0.0",
)

# CORS middleware...
app.add_middleware(...)

# Include admin router
app.include_router(admin_router)  # <-- ADD THIS

# In-memory catalog storage...
catalog: List[Offering] = []
```

### Step 3: Restart Your API

```bash
cd /Users/donovanmchenry/Projects/njitschedulepro/api
uvicorn app.main:app --reload
```

## Available Admin Endpoints

Once integrated, you'll have these new endpoints:

### 1. Trigger Catalog Update

**POST** `/admin/update-catalog`

Triggers the scraper to fetch fresh data and update the catalog.

**Request Body:**
```json
{
  "term": "202501",  // Optional: specific term
  "backup": true     // Whether to backup existing catalog
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Catalog update started in background...",
  "details": {
    "term": "202501",
    "backup": true
  }
}
```

**Example with curl:**
```bash
curl -X POST http://localhost:8000/admin/update-catalog \
  -H "Content-Type: application/json" \
  -d '{"backup": true}'
```

### 2. Check Update Status

**GET** `/admin/update-status`

Check if an update is running or view results of the last update.

**Response (In Progress):**
```json
{
  "status": "in_progress",
  "message": "Update is currently running..."
}
```

**Response (Completed):**
```json
{
  "status": "completed",
  "message": "Last update completed successfully",
  "details": {
    "success": true,
    "term": "202501",
    "stdout": "...log output..."
  }
}
```

**Example with curl:**
```bash
curl http://localhost:8000/admin/update-status
```

### 3. Reload Catalog (Without Scraping)

**POST** `/admin/reload-catalog`

Reload catalog from existing CSV files without running the scraper. Useful after manual CSV updates or after a background scrape completes.

**Response:**
```json
{
  "status": "success",
  "message": "Successfully reloaded 1234 offerings from 45 files",
  "details": {
    "file_count": 45,
    "offering_count": 1234,
    "loaded_at": "2025-01-11T12:34:56"
  }
}
```

**Example with curl:**
```bash
curl -X POST http://localhost:8000/admin/reload-catalog
```

## Frontend Integration

### React Example

Create an admin panel in your web app:

```typescript
// AdminPanel.tsx
import { useState } from 'react';
import { apiUrl } from '@/lib/api';

export function AdminPanel() {
  const [updating, setUpdating] = useState(false);
  const [status, setStatus] = useState<string>('');

  const triggerUpdate = async () => {
    try {
      setUpdating(true);
      const response = await fetch(apiUrl('/admin/update-catalog'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup: true }),
      });
      const data = await response.json();
      setStatus(data.message);

      // Poll for status
      checkStatus();
    } catch (error) {
      setStatus('Error triggering update');
    }
  };

  const checkStatus = async () => {
    try {
      const response = await fetch(apiUrl('/admin/update-status'));
      const data = await response.json();
      setStatus(data.message);

      if (data.status === 'in_progress') {
        // Check again in 30 seconds
        setTimeout(checkStatus, 30000);
      } else {
        setUpdating(false);
      }
    } catch (error) {
      setStatus('Error checking status');
      setUpdating(false);
    }
  };

  const reloadCatalog = async () => {
    try {
      const response = await fetch(apiUrl('/admin/reload-catalog'), {
        method: 'POST',
      });
      const data = await response.json();
      setStatus(data.message);
    } catch (error) {
      setStatus('Error reloading catalog');
    }
  };

  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg">
      <h2 className="text-xl font-bold mb-4">Admin Controls</h2>

      <div className="space-y-4">
        <button
          onClick={triggerUpdate}
          disabled={updating}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {updating ? 'Updating...' : 'Update Course Catalog'}
        </button>

        <button
          onClick={reloadCatalog}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Reload Catalog
        </button>

        {status && (
          <div className="p-4 bg-gray-100 dark:bg-gray-700 rounded">
            <p className="text-sm">{status}</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

### Simple HTML Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>NJIT Admin</title>
</head>
<body>
  <h1>Course Catalog Admin</h1>

  <button onclick="triggerUpdate()">Update Catalog</button>
  <button onclick="checkStatus()">Check Status</button>
  <button onclick="reloadCatalog()">Reload Catalog</button>

  <div id="status"></div>

  <script>
    const API_URL = 'http://localhost:8000';

    async function triggerUpdate() {
      const response = await fetch(`${API_URL}/admin/update-catalog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup: true })
      });
      const data = await response.json();
      document.getElementById('status').innerText = data.message;
    }

    async function checkStatus() {
      const response = await fetch(`${API_URL}/admin/update-status`);
      const data = await response.json();
      document.getElementById('status').innerText = data.message;
    }

    async function reloadCatalog() {
      const response = await fetch(`${API_URL}/admin/reload-catalog`, {
        method: 'POST'
      });
      const data = await response.json();
      document.getElementById('status').innerText = data.message;
    }
  </script>
</body>
</html>
```

## Security Considerations

⚠️ **Important**: These endpoints can trigger resource-intensive operations. You should add authentication!

### Add API Key Authentication

```python
# In admin_endpoints.py

from fastapi import Header, HTTPException

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "your-secret-key-here")

async def verify_admin(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# Add to each endpoint:
@router.post("/update-catalog")
async def trigger_catalog_update(
    request: UpdateRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_admin)  # Add this
):
    ...
```

### Use in Frontend

```typescript
const response = await fetch(apiUrl('/admin/update-catalog'), {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-secret-key-here'  // Add this
  },
  body: JSON.stringify({ backup: true })
});
```

## Testing

### Test from Command Line

```bash
# Trigger update
curl -X POST http://localhost:8000/admin/update-catalog \
  -H "Content-Type: application/json" \
  -d '{"backup": true}'

# Check status
curl http://localhost:8000/admin/update-status

# Reload catalog
curl -X POST http://localhost:8000/admin/reload-catalog
```

### Test from Browser

Visit http://localhost:8000/docs to see the interactive API documentation (Swagger UI).

## Workflow

Recommended workflow for updates:

1. **Trigger Update**: Call `/admin/update-catalog`
   - Runs in background (5-15 minutes)
   - Scrapes fresh data
   - Backs up old catalog
   - Saves new CSVs

2. **Monitor Progress**: Poll `/admin/update-status`
   - Check every 30 seconds
   - Wait for `status: "completed"`

3. **Reload Catalog**: Call `/admin/reload-catalog`
   - Immediately loads new data
   - No API restart needed

4. **Done**: Users see fresh data

## Alternative: Automatic Reload

If you want the API to automatically reload after updates, you can:

1. Run API in development mode with `--reload` flag
2. Use a file watcher to restart API when CSVs change
3. Have the updater script call the reload endpoint

## Troubleshooting

### "Updater script not found"

Make sure the scraper directory is at `/Users/donovanmchenry/Projects/njitschedulepro/scraper/`

Or update the path in `admin_endpoints.py`:

```python
scraper_dir = Path("/custom/path/to/scraper")
```

### Updates Time Out

Increase the timeout in `admin_endpoints.py`:

```python
result = subprocess.run(
    cmd,
    timeout=3600,  # 60 minutes instead of 30
)
```

### Permission Denied

Make sure the auto_update_scheduler.py is executable:

```bash
chmod +x /Users/donovanmchenry/Projects/njitschedulepro/scraper/auto_update_scheduler.py
```

## Next Steps

1. Add the admin endpoints to your API
2. Test the endpoints with curl
3. Create an admin panel in your frontend
4. Add authentication for security
5. Set up monitoring/alerting

Happy updating! 🚀
