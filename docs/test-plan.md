# Milestone A verification

Automated backend tests cover identity spoofing, operator/device credential separation, company isolation over REST and WebSockets, disabled-device access, duplicate replay, atomic conflict rollback, late arrivals, recorded-time ordering, assignment-at-capture, pagination, invalid fixes, timestamp/range/body/batch bounds, and stale/offline state.

Frontend tests cover route segmentation for no-fix events, long gaps and device changes. Build the production bundle as a separate check.

## Local acceptance

1. Start Compose; migration must complete and `/api/v1/health` return ok.
2. Seed and start ten devices. Sign into the `demo` workspace and confirm markers and timestamps change.
3. Observe simulated outages and no-fix periods; old valid locations remain visible but turn stale. Stop simulation for 120 seconds and confirm offline state.
4. Load a journey with outages, play it and inspect gaps. Short no-fix intervals also break tracks. Empty ranges show an explicit empty state.
5. Sign out and sign in as `other`; no `demo` devices appear. Attempt other-company asset IDs and WebSocket organization selections; access must fail.
6. Restart backend and simulator; queued records replay without duplicate positions and no latest-position regression.
7. Confirm PostgreSQL's unique constraints and migration by replaying the same batch concurrently; exactly one stored record per sequence. Verify PostGIS with `SELECT PostGIS_Version()`.

## Fleet scenarios

Seed 100 devices using `docker compose --env-file infrastructure/.env -f infrastructure/docker-compose.yml run --rm seed python /workspace/scripts/seed_demo_company.py --devices 100 --output /private/demo-credentials.json`.

Run the simulator for 1, 10 and 100 devices with `--devices N --ticks 120`. With Compose, override the simulator command: `python /workspace/simulator/fleet_simulator.py --url http://backend:8000 --credentials /private/demo-credentials.json --state /state/queue.json --devices 100 --ticks 120`. Do not run competing processes on the same state file. The simulator reports acknowledged sample count, request failures, elapsed time, throughput and p95 request latency. These are observations, not SLAs.

SQLite tests are a fast correctness layer; they do not certify PostgreSQL concurrency, migration deployment, map rendering or operational capacity. Record actual results in `verification.md` and do not mark full acceptance complete until the Compose workflow has been exercised.
