# Verification record — 2026-10-27

## Account/admin update — 2026-10-28

- The original 14 backend tests still pass. Seven account/admin tests cover password hashing, login/logout, expiry, throttling, platform-admin authorization, membership changes, organization disabling, password reset/revocation, self-protection and seed preservation.
- Four admin-form tests pass: create organization, create user with memberships, preserve blank passwords/protect own role, and display server errors without discarding the form.
- Frontend production build passes (75 modules). Validation used an isolated Windows dependency directory, preserving the user's WSL `node_modules`.
- Migration `0002` and Alembic drift check passed on a copy of the existing SQLite database. The user's active database was not migrated during testing; restart `python3 app.py` to migrate and provision account login.
- A real HTTP smoke test on the migrated copy passed login, platform organization/user listing and logout.
- No browser is connected, so visual browser verification remains pending. PostgreSQL-specific migration/runtime validation remains pending as previously recorded.

## Initial foundation

Implemented Milestone A foundation; full Docker/browser acceptance remains pending.

| Check | Result |
|---|---|
| Backend automated tests | 14 passed; one upstream Starlette/httpx deprecation warning |
| Frontend route segmentation tests | 2 passed |
| Production React/Vite build | Passed; 73 modules transformed |
| Python syntax compilation | Passed |
| SQLite Alembic upgrade | Passed |
| Alembic model/schema drift check | No new upgrade operations detected |
| Repeatable demo seed | Passed; two companies, expanded primary company to 100 devices |
| Live API readback | Passed: 100 scoped devices, 67 valid latest fixes, first asset history ordered and duplicate-free |
| Docker Compose configuration | Validated; Docker config access warning from sandbox |
| PostgreSQL/PostGIS containers and migrations | Not run: Docker engine is stopped/unavailable |
| Browser visual / interaction review | Not run: browser automation inventory is empty |

Real HTTP smoke runs against the local SQLite-backed FastAPI server:

| Devices | Ticks | Acknowledged samples | Pending simulated-outage samples | Request failures | Elapsed | Request p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 2 | 0 | 0 | 4.11 s | 2.06 s |
| 10 | 3 | 30 | 0 | 0 | 6.73 s | 2.23 s |
| 100 | 2 | 138 | 62 | 0 | 13.00 s | 2.72 s |

These short smoke runs use a 0.2-second acquisition interval and deliberately simulated outages. They establish connectivity and replay acknowledgments, not sustainable capacity or complete outage-cycle acceptance. The simulator's queue retains pending samples. Long-duration, PostgreSQL and UI tests are still required before declaring all Milestone A acceptance criteria met.

Environment: Windows ARM64, Python 3.11, portable Node 22.22.0. Native PostgreSQL driver wheel installation was unavailable on this Python architecture; PostgreSQL dependencies are a separate optional extra, installed in Docker. The frontend build uses Vite's native config loader to avoid sandbox ancestor-directory reads. A production bundle preview was served, but no visual review was possible.
