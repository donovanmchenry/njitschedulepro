# Active scheduling semester

The schedule builder targets **Spring 2027 (`202710`)**. The existing GitHub
Actions workflow uses NJIT's anonymous public registration search API, explicitly
selects this term, validates pagination, unique section counts, and every exported row,
and rebuilds `web/public/catalog/` from the root `courseschedules/*.csv` files.
The Fall 2026 Room Finder timetable remains in `courseschedules/202690/`.

To refresh just the builder without re-exporting the Room Finder timetable:

```sh
gh workflow run update-schedules.yml --repo donovanmchenry/njitschedulepro --ref main -f refresh_room_finder=false
```

Wait for the data commit and frontend/API deployments before running:

```sh
python3 scripts/check_schedule_term.py
```

This checks the live catalog semester, agreement between browser and API course
and section counts, schedule generation, and Spring calendar export dates.
The asset build also publishes `catalog.csv.gz`, a compressed copy of the
complete CSV export. The API fetches this snapshot at startup and when the
workflow invokes its authenticated reload endpoint with the new data commit
SHA. A failed or wrong-semester download preserves the current in-memory
catalog. This avoids depending on a backend rebuild for data-only commits.
The solver rejects browser requests for a different catalog semester instead
of silently using an old deployment's offerings.

Calendar exports infer Spring dates from the offerings' term: January 19 to
May 3, 2027, inclusive. Source:
https://www.njit.edu/registrar/spring-2027-academic-calendar

When moving to another semester, update the workflow's explicit term and
validation argument, add the official class dates in `api/app/terms.py`, and
update `ACTIVE_TERM` in `web/src/lib/catalog.ts` and the production verification script. Do not rely on
Banner's default selected term, which can be Winter during Spring planning.
