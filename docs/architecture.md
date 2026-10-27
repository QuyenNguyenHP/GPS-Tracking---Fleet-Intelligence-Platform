# Architecture

Milestone A uses a modular monolith: FastAPI routes delegate to authentication and telemetry/location services; SQLAlchemy stores records in PostgreSQL, with Alembic controlling schema changes. PostGIS is enabled by the first migration. Raw coordinates remain scalar WGS84 values until spatial queries require geometry indexes.

Device POST → bearer credential hash lookup → schema/identity validation → per-device transaction lock → duplicate-safe insert → conditional latest-position upsert → commit → acknowledgment.

The unique `(device_id, sequence_number)` database constraint makes retries safe. A reused sequence with different data fails the entire batch with 409. Latest position changes only for a strictly newer valid capture timestamp. No-fix records are retained in the same event store and do not update the last valid fix. Last-seen time records successful receipt, including duplicate retry traffic.

Operator REST and WebSocket access require a user token plus an allowed organization membership. WebSockets use an initial authentication frame, then reauthorize and send full snapshots every two seconds. This avoids an in-memory broadcast consistency dependency in the first prototype; at large fleet sizes replace it with authorized event deltas and a shared pub/sub mechanism.

The simulator stores its sequence counter and unacknowledged samples before transmitting. It sends recent records before older records, duplicates samples deliberately, and removes only acknowledged sequence numbers. One simulator process must own each queue file. State survives restart. Queue capacity is 10,000 per device; reaching it stops acquisition explicitly without dropping retained samples. Retry is at the configured interval; exponential backoff and device firmware are deferred.

React uses REST for history and reconnect snapshots, then WebSockets for updates. History polylines split on explicit no-fix events, device changes, or intervals longer than 30 seconds. Replay shows recorded samples, not inferred road travel.

Official implementation references: [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/), [PostgreSQL INSERT / conflict handling](https://www.postgresql.org/docs/17/sql-insert.html), [React Leaflet](https://react-leaflet.js.org/).
