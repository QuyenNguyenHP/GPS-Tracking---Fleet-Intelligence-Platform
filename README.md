# GPS Tracking & Fleet Intelligence Platform

Milestone A software foundation: authenticated telemetry → durable history → live fleet map → route playback. Hardware is not required. The current project folder is the repository root.

## Account login and admin page

Sign in with a **username and password**. The default local platform-admin credentials are **admin / admin123**. Passwords require at least eight characters. Change this development password before deploying outside your local environment.

Restart `python3 app.py` to apply the account migration and prepare the admin account automatically for the default SQLite database. Existing device keys and history are retained. For Docker, rebuild the services and run the seed command again. For a custom database connection, run migrations and seeding explicitly as described in [account setup](docs/accounts-and-admin.md).

After signing in as `admin`, use **Organizations** to create/rename/disable companies and **Users** to create accounts, assign workspaces, change platform-admin access, disable accounts or reset passwords. Use **Fleet workspace** to return to the map. The separate `other.viewer` account can verify regular-user restrictions. Seeding again does not reset existing accounts.

## Development: separate backend and frontend terminals

### Quick start in WSL / Ubuntu

From `backend`, install once and start the development server:

```bash
sudo python3 -m pip install --break-system-packages -r requirements.txt
python3 app.py
```

This system-wide install follows the selected development preference; it can conflict with Ubuntu-managed Python packages. Run the server without sudo. Python 3.11+ is required. The launcher applies migrations and, when `DATABASE_URL` is unset, prepares demo identities in the local SQLite database automatically. If `DATABASE_URL` is set, it migrates that database but does not seed it. This launcher is for local development.

In another terminal, from `frontend`:

```bash
npm ci
npm run dev
```

Open http://localhost:5173. Sign in as `admin` using the generated account password described above. Subsequent starts require only `python3 app.py` and `npm run dev` in their respective directories. Run the simulator separately for moving positions.

### PowerShell setup

Use Python 3.11+ and Node.js 22+ (including npm). These commands use SQLite for local development, so Docker is not required. PostgreSQL/PostGIS acceptance still uses the Compose setup below. Run each terminal from this project folder initially.

First-time setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e 'backend[test]'
cd frontend
npm ci
cd ..
```

Terminal 1 — backend with automatic reload:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe ../scripts/seed_demo_company.py --output ../infrastructure/demo-credentials.json
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Migration and seed commands are safe to rerun. Leave `DATABASE_URL` unset to use the local `backend/fleet.db`. API docs: http://127.0.0.1:8000/docs.

Terminal 2 — frontend with hot reload:

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` HTTP and WebSocket requests to the backend on port 8000. Sign in with the generated `admin` account, then choose **Fleet workspace** for the map.

Terminal 3 — optional moving demo devices:

```powershell
.\.venv\Scripts\python.exe simulator/fleet_simulator.py --url http://127.0.0.1:8000
```

Stop each process with Ctrl+C. If `npm` is not recognized, install Node.js 22+ with npm and reopen the terminals. If PowerShell blocks `npm.ps1`, use `npm.cmd ci` / `npm.cmd run dev`. Stop any Docker backend using port 8000 before starting the local backend.

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

Open **http://localhost:8080**. Sign in as `admin` with the generated password from `infrastructure/demo-credentials.json`. A second organization, `other`, has a separate `other.viewer` account for isolation checks. Keep the simulator terminal running. No credentials are embedded in source code.

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
npm run test:ui
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

This is a local prototype. Human access uses password login with eight-hour sessions. Platform administrators manage organizations, accounts and memberships; fleet reads remain organization-scoped. Legacy operator tokens remain available for existing read-only API integrations, but cannot administer the platform. Fine-grained organization roles, clustering, advanced analytics, alerts, hardware, production TLS, retention and deployment hardening are later work. WebSockets send fresh organization snapshots every two seconds. History requests are limited to seven days and paginated; the UI refuses more than 50,000 samples rather than silently truncating a route.
