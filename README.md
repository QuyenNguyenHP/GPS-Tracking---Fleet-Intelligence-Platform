# GPS Tracking & Fleet Intelligence Platform

Milestone A software foundation: authenticated telemetry → durable history → live fleet map → route playback. Hardware is not required. The current project folder is the repository root.

## Run locally with Docker

Prerequisites: Docker Desktop with its Linux engine running (Compose v2). The PostGIS service uses `linux/amd64`; Windows ARM requires Docker's amd64 emulation support.

Run these commands from this folder in PowerShell:

```powershell
Copy-Item infrastructure/.env.example infrastructure/.env
# Edit infrastructure/.env: replace POSTGRES_PASSWORD with a random URL-safe password.
docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml up --build -d
docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml run --rm seed
docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml run --rm simulator
```

Open **http://localhost:8080**. Select organization `demo` and paste its `operator_token` from the generated private `infrastructure/demo-credentials.json`. A second organization, `other`, has a different operator token for isolation checks. Keep the simulator terminal running. No credentials are embedded in source code.

- API and interactive contract: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- The default seed creates ten devices plus one device in the second organization.
- Map tiles need internet access; all tracks are synthetic Singapore-area trajectories, not actual road routing.
- For history, select a device, set the time range (browser local time), and choose **View journey**. The default end time is set when the page opens; advance it to include later samples.
- Stop services with `docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml down`. Database and simulator queue volumes are retained. Do not use `down -v` unless you intend to erase them.

## Development and checks

Python 3.11+ and Node 22+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e 'backend[test]'
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm ci
npm test
npm run build
cd ..
```

For development against PostgreSQL, install `backend[postgres,test]`, set `DATABASE_URL` to a reachable `postgresql+psycopg://...` connection, run `alembic upgrade head` from `backend`, then start `uvicorn app.main:app`. The Compose database intentionally has no public host port; use the backend container or add a loopback-only development port. Native Windows ARM Python has no compatible psycopg binary wheel in the checked versions; use Docker for PostgreSQL on that platform. SQLite development does not require that driver.

For a lightweight SQLite developer smoke run (not a PostgreSQL substitute), omit `DATABASE_URL`, run migrations from `backend`, and run the seed command from the same directory using `--output ../infrastructure/demo-credentials.json`. Start the backend there; start `npm run dev` from `frontend`, then run the simulator from the root. SQLite is only a development/test fallback; PostGIS capabilities are available in Compose but spatial calculations are deferred.

Run database-backed tests inside Compose with:

```powershell
docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml exec backend pytest -q
```

Those tests use isolated SQLite databases by default. See [test plan](docs/test-plan.md) for PostgreSQL acceptance and load checks. Do not point test reset operations at a database containing real data.

## Layout and scope

- `backend/`: FastAPI modular monolith, SQLAlchemy entities, Alembic migrations, tests.
- `frontend/`: React + Leaflet live map, device list, history and playback.
- `simulator/`: concurrent synthetic fleet, persistent queue, retries, outages, no-fix and late replay.
- `infrastructure/`: Docker Compose and environment template.
- `scripts/`: repeatable demo provisioning.
- `docs/`: [project spec](docs/PROJECT_SPEC.md), architecture, contracts, security and test plan.
- `firmware/xiao-esp32s3-l76k/`: reserved for Milestone B; no unverified pin assignments.

This is a local prototype. Human access uses generated operator bearer tokens with organization membership; a user login/session system, full RBAC administration, clustering, advanced analytics, alerts, hardware, production TLS, retention and deployment hardening are later work. WebSockets send fresh organization snapshots every two seconds. History requests are limited to seven days and paginated; the UI refuses more than 50,000 samples rather than silently truncating a route.
