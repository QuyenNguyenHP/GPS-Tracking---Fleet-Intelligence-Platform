# Implemented API

| Endpoint | Authentication | Behavior |
|---|---|---|
| `GET /api/v1/health` | none | Database readiness check |
| `POST /api/v1/telemetry` | device bearer | One sample |
| `POST /api/v1/telemetry/batch` | device bearer | Atomic batch, up to 200 samples |
| `GET /api/v1/assets` | operator + organization header | Authorized assets |
| `GET /api/v1/devices/latest` | operator + organization header | Latest position, last-seen, live/stale/offline |
| `GET /api/v1/assets/{id}/positions` | operator + organization header | Ordered recorded-time history including no-fix events |
| `WS /api/v1/ws/locations` | first frame | Authorized snapshots every two seconds |

Operator headers: `Authorization: Bearer <operator token>` and `X-Organization-ID: demo`. Membership is checked server-side. Other-company asset IDs return 404.

History requires timezone-aware `from` and `to` with `to > from`, maximum seven days. `limit` defaults to 1,000 (max 5,000). Use returned `next_offset` for subsequent pages until null. Ordering is capture timestamp then stable event ID; concurrent backfill can change offset boundaries, so rerun a completed historical interval after uploads settle for a consistent export.

WebSocket first frame (within five seconds): `{"token":"<operator token>","organization_id":"demo"}`. No token in URL. Server closes unauthorized connections with code 1008. Reconnect with a fresh snapshot. Token revocation and membership are rechecked before each snapshot.

States: **offline** if last successful report is older than 120 seconds or absent; otherwise **stale** if the last valid capture or last report is older than 30 seconds; otherwise **live**. Position freshness and connection state are separate. A currently reporting device without a fix is stale.

HTTP errors: 401 invalid credential, 403 identity/membership mismatch, 404 inaccessible asset, 409 conflicting sequence, 413 body size, 422 schema/range validation. FastAPI uses a `detail` string or validation-error array.
