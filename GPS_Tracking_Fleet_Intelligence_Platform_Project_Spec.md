# GPS Tracking & Fleet Intelligence Platform

**Product requirements, system architecture, device concept, and implementation roadmap for Codex**

| Field            | Value                                                                                                                |
| ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| Version          | **2.0**                                                                                                        |
| Date             | **2026-10-27**                                                                                                 |
| Status           | **Product vision agreed; architecture and initial requirements proposed; implementation pending**              |
| Initial hardware | **Seeed XIAO ESP32S3 + L76K GNSS, Wi-Fi, USB-powered**                                                         |
| Final product    | **Multi-device, multi-company GPS data platform with live tracking, history, processing, analytics, and APIs** |

> **Critical product principle:** The GPS tracker is an edge device, **not the final product**. The final deliverable is an end-to-end platform that can collect location data from many devices, retain it securely, visualize it, and support different business applications built on the same location-data infrastructure. Fleet management for a transportation company is the primary example, but the platform must not be hardcoded only for vehicles.

---

## 1. Executive Product Vision

Build a reusable **GPS Tracking & Location Intelligence Platform** comprising:

1. **Tracking hardware:** Small ESP32-based devices that obtain GNSS positions and send telemetry over Wi-Fi or 4G LTE. Support both externally powered and battery-powered versions.
2. **Central data server:** Secure device enrollment, authentication, ingestion, durable historical storage, quality checks, live position state, event processing, and data-access APIs.
3. **Live tracking application:** Web maps showing all authorized devices/assets and the latest valid positions, status, speed, heading, and last report time.
4. **Historical movement application:** Date-range tracks, trip segmentation, route replay, distance calculations, stops, and exports.
5. **Business applications:** Fleet and vehicle operations, geofences, alerts, utilization, reporting, and later domain-specific analytics for vehicles, equipment, containers, or other assets.
6. **Integration layer:** Documented APIs, webhooks, and exports so other software can reuse the collected location data.

**Example:** A logistics company has 100 trucks. Each truck has a GPS tracker. The company can see all trucks on a map, inspect an individual truck's movements, analyze routes and stop times, receive configurable alerts, and generate fleet reports. Other companies can use the same hosted platform while seeing only their own assets.

### What is in scope, and what is not

- **In scope:** Physical GPS devices, their firmware, a secure and scalable backend, a database, map UI, location history, fleet features, analytics, and an extendable API architecture.
- **Not required in the first release:** Native mobile apps, custom miniature PCB, enterprise-scale streaming infrastructure, AI prediction, live driver identification from GPS alone, fuel consumption without separate data, or accurate indoor/tunnel positioning.
- **Do not implement everything at once.** Build a working vertical slice from GPS simulator to server to map, then expand in clear phases.

---

## 2. Product Architecture

```text
               GNSS / GPS / Galileo / BeiDou satellites
                               |
                               v
                    TRACKING / EDGE LAYER
     +-----------------------------------------------------+
     | ESP32 + GNSS, or ESP32 + cellular modem with GNSS   |
     | Firmware: sample, validate, timestamp, buffer, send |
     | Variants: Wi-Fi / 4G ; wired / battery              |
     +--------------------------+--------------------------+
                                |
                     Wi-Fi or 4G LTE / Internet
                                |
                     HTTPS/TLS (MQTT later)
                                v
                      DATA PLATFORM LAYER
     +-----------------------------------------------------+
     | Secure Device Ingestion + Device Registry           |
     | AuthN/AuthZ + Organizations + Users + Fleet/Assets  |
     | GNSS Validation, Idempotency, Offline Data Handling |
     | Latest Position + Historical Position Store         |
     | Trip/Stop Processing + Geofences + Event Rules       |
     | Real-Time Updates + APIs + Reporting + Integrations |
     +-------------------------+---------------------------+
                               |
          +--------------------+---------------------+
          |                    |                     |
          v                    v                     v
  LIVE MAP / TRACKING   ROUTE HISTORY         BUSINESS APPS
  Asset status          Trip playback         Fleet management
  Real-time markers     Stops / distances     Analytics and KPIs
  Search / filter       Historical reports    Alerts / geofences
  Multi-vehicle view    Export / audit        External integrations
```

### Architectural principles

- **One platform, many devices and applications.** Do not build separate servers for each device hardware version.
- **Hardware-agnostic ingestion.** A future third-party GPS tracker may use the same versioned data contract and authentication scheme.
- **Separation of concerns.** Distinguish raw acquisition, validated location, latest state, business events, and calculated analytics.
- **Multi-tenant from the data-model level.** Organizations/companies, assets, users, and permissions must be first-class concepts; prevent cross-company data leakage.
- **Extendable processing.** Initial calculation jobs can run in the backend; add background workers/queues only when needed.
- **Accuracy first.** Never fabricate GPS fixes or claim precise behavior not supported by available sensor data.

---

## 3. Product Modules and Release Priorities

| Module                        | Core capability                                                                 | Delivery priority            |
| ----------------------------- | ------------------------------------------------------------------------------- | ---------------------------- |
| Device registry               | Register, enable/disable, monitor devices, store firmware and network metadata  | MVP                          |
| Telemetry ingestion           | Authenticated single/batch upload; schema validation; duplicate-safe processing | MVP                          |
| Data server                   | Persist telemetry, positions, device status, and history                        | MVP                          |
| Live map                      | Show latest positions for one or many devices; online/stale/offline status      | MVP                          |
| Route history                 | Query date ranges, connect valid points, visualize gaps, playback               | MVP                          |
| Organizations and users       | Company workspaces and authorized member access                                 | MVP foundation               |
| Assets and device assignments | Associate device with vehicle/container/equipment over time                     | Fleet MVP                    |
| Fleet management              | Fleet groups, vehicles, driver records, search and filters                      | Fleet MVP                    |
| Trip/stop analytics           | Trips, distance, duration, stop periods, summaries                              | Fleet MVP                    |
| Geofences and alerts          | Enter/exit, stopped-too-long, device offline, low battery                       | Fleet MVP                    |
| Analytics / reporting         | Dashboard KPI cards, per-asset summaries, CSV/GeoJSON exports                   | Fleet MVP                    |
| API/webhooks                  | Controlled programmatic access to data and events                               | After core MVP               |
| Config / OTA                  | Remote device config, firmware lifecycle, diagnostics                           | Later                        |
| Optimization / AI             | Anomaly detection, route efficiency, advanced prediction                        | Later, after sufficient data |

### User roles (proposed)

- **Platform administrator:** Manage platform-wide settings and tenant lifecycle.
- **Organization administrator:** Manage users, fleets, vehicles, device assignments, and organization settings.
- **Fleet manager:** View and analyze authorized assets; handle fleet alerts and reports.
- **Viewer/dispatcher:** View permitted maps, history, and basic reports without sensitive administration rights.
- **Device:** Machine identity allowed to upload its own telemetry, **not** a normal human account.

Use strict server-side authorization and organization scoping; do not rely on frontend filtering.

---

## 4. Tracking Hardware: Versions, Choices, and Constraints

### 4.1 Planned hardware variants

| Version | Connectivity | Power                     | Typical role                                                      |
| ------- | ------------ | ------------------------- | ----------------------------------------------------------------- |
| V1      | Wi-Fi        | Wired USB 5 V             | First end-to-end prototype, hotspot-enabled vehicles, lab testing |
| V2      | Wi-Fi        | Rechargeable battery      | Portable objects with Wi-Fi coverage                              |
| V3      | 4G LTE + SIM | Wired / automotive supply | Independent vehicle tracker for operational deployment            |
| V4      | 4G LTE + SIM | Rechargeable battery      | Portable outdoor asset tracking without Wi-Fi                     |

**GNSS obtains the position. Wi-Fi/4G only transmits it.** Wi-Fi-only devices need access to a network (for example, a car hotspot). For independently tracked vehicles, the cellular version is normally more practical.

### 4.2 MCU decision

- **Preferred initial board:** Seeed **XIAO ESP32S3** (standard/non-Sense). Approximate board footprint: **21 x 17.8 mm**.
- **Alternative:** XIAO ESP32C3; sufficient for a simpler tracker but with less processing/memory headroom.
- **Why S3:** Similar controller-board footprint, dual-core capability and more headroom for TLS, buffers, and future software complexity.
- Neither ESP32 board provides cellular networking or dedicated GNSS by itself.
- For a design with multiple UART peripherals, investigate the XIAO ESP32S3 Plus or appropriate alternative; verify the chosen board's pinout and antenna setup.

### 4.3 GNSS decision

- **Initial GNSS receiver:** Seeed **L76K** XIAO-compatible GNSS board, approximately **18 x 21 mm**, with a separate ceramic active GNSS antenna connected by RF cable.
- UART/NMEA-based location reading.
- Initial sampling target: around **1 Hz**; transmit new data about **every 5 seconds**, configurable later.
- Vendor accuracy figures (such as ~2 m CEP) represent favorable specified conditions, **not guaranteed in-car performance**.
- Useful data: fix status, latitude, longitude, UTC time, speed, heading, satellite count, and GNSS quality indicators when available.
- The firmware must explicitly handle no-fix and stale-fix cases.

### 4.4 Car/dashboard installation

- The device may be **visible on the dashboard near the windshield**. It does not need to be fully hidden.
- Prefer a **nonmetallic enclosure**; GNSS antenna faces toward the sky and should not be blocked by metal or RF-hostile structures.
- Windshield tint, conductive coatings, tunnels, garages, urban canyons, and nearby electronics can reduce reception.
- When GNSS is lost, keep the most recent confirmed position and its timestamp, mark it stale, and resume only after a valid fix. Historical segments across outages should be broken or dashed, not assumed to be the exact traveled road.
- Keep the mounted enclosure secure and outside the driver's sight line. Vehicle cabin heat must be considered, especially before introducing a battery.

### 4.5 Compact enclosure targets

- **Aspirational optimized Wi-Fi design:** approximately **40 x 35 x 15 mm**.
- **Provisional modular prototype allowance:** approximately **45 x 40 x 20-25 mm**.
- These are **targets, not measured verified dimensions**; antenna clearance, headers, connectors, cables, and PCB integration may change the result.
- Proposed vertical layout: plastic cover -> GNSS antenna -> L76K board -> ESP32S3 board -> base / USB / mounting pad. Verify RF clearance before finalizing.
- Optimize size **after** working hardware and reliable RF reception. A custom PCB can remove excessive headers and integrate the design.

### 4.6 Cellular version

- Investigate an **ESP32-S3 + LTE Cat-1 modem with GNSS**, e.g. an appropriate **SIM7670-series evaluation board**, for rapid prototyping.
- A modem with integrated GNSS may avoid needing a separate L76K on the LTE prototype.
- Verify regional LTE bands, operator/SIM compatibility, GNSS availability on the exact SKU, antennas, power peaks, USB needs, and board size before purchasing.
- The cellular evaluation board is a **prototype**, not the intended final compact enclosure.
- Avoid relying on 2G/3G-only modems in markets where those networks are retired.

### 4.7 Power versions

- **Phase 1:** Stable USB 5 V supply. No internal battery.
- **Wired automotive future:** Proper fused and protected automotive supply from 12/24 V, with reverse polarity, transient/load-dump and voltage conversion protections; decide ACC-triggered versus always-on operation.
- **Battery future:** Protected Li-ion/LiPo with charge management, voltage/temperature monitoring, sleep modes, safe thermal design, and measured runtime.
- Test complete-system consumption; modem transmission bursts and GNSS duty cycle matter more than MCU-only sleep figures.

---

## 5. Firmware and Telemetry Requirements

### 5.1 Firmware responsibilities

1. Boot, identify firmware version and load secure configuration.
2. Read GNSS and distinguish valid/invalid fix states.
3. Timestamp each sample **at acquisition**, in UTC.
4. Add monotonically increasing or otherwise durable unique sample identifiers for retry deduplication.
5. Persist unsent valid samples to a **bounded offline queue** when needed.
6. Send authenticated HTTPS/TLS requests, with batch retry and exponential backoff.
7. Await server acknowledgement before retiring queued records.
8. Provide connectivity, GNSS quality, power and device-health metadata.
9. Keep GNSS, Wi-Fi/LTE, queue, configuration, and power modules loosely coupled.
10. Provide controlled logging and safe operation after reset/reboot.

### 5.2 Sample telemetry payload

```json
{
  "schema_version": 1,
  "device_id": "GPS-001",
  "sequence_number": 1042,
  "recorded_at": "2026-10-27T01:10:00Z",
  "location": {
    "fix_valid": true,
    "latitude": 1.30001,
    "longitude": 103.80001,
    "speed_kmh": 35.6,
    "heading_deg": 125.0,
    "satellites": 12,
    "hdop": 0.9
  },
  "status": {
    "network_type": "wifi",
    "battery_percent": null,
    "external_power": true,
    "firmware_version": "0.1.0"
  }
}
```

**Semantics and rules:**

- Example coordinates are illustrative, not live data. Coordinates use WGS84 decimal degrees.
- `recorded_at` is capture time; backend adds `received_at` (server time) to preserve latency and offline replay context.
- `device_id` in JSON must match authenticated device identity; **never trust a caller to choose someone else's ID**.
- Sequence number uniqueness is scoped to the device and must remain safe across reboots; alternatively use a persistent UUID for each sample.
- Invalid/no-fix status may be submitted as a **status/heartbeat event** without pretending that stale coordinates represent a valid new position.
- Optional fields should be `null`/omitted according to the agreed versioned schema, not invented.
- Report 1, 5, 30, or 60 seconds as configurable choices. GNSS acquisition rate and network reporting rate are separate.
- Firmware must have finite queue limits and documented behavior when storage fills.

### 5.3 Back-of-envelope volume

Assuming one message per interval around the clock:

| Devices | Interval | Messages per day | Messages per 30-day period |
| ------: | -------: | ---------------: | -------------------------: |
|       1 |      5 s |           17,280 |                    518,400 |
|     100 |      5 s |        1,728,000 |                 51,840,000 |
|   1,000 |      5 s |       17,280,000 |                518,400,000 |
|     100 |     60 s |          144,000 |                  4,320,000 |

Actual data-storage and bandwidth costs depend on protocol overhead, schema, indexes, geometry, retention, and compression. These are sizing illustrations, not performance guarantees. **Design for data retention and partitioning early**, especially if moving beyond tens or hundreds of vehicles.

---

## 6. Backend Services and Data Pipeline

```text
Device -> HTTPS ingress -> Authenticate device -> Validate schema
       -> Idempotent write (timestamped position + status)
       -> Update latest valid position only when newer
       -> Publish live update to authorized subscribers
       -> Background calculations: trips, stops, geofences, alerts, summaries
       -> API / reports / export / integration consumers
```

### Minimum backend capabilities

- Per-device authentication, key/token rotation and revocation.
- Rate limits, input validation, payload-size bounds and ingestion diagnostics.
- Single-record and batch uploads for reconnect/backfill.
- Accepted sample acknowledgements and safe duplicate handling.
- Raw accepted position storage plus quality flags; do not silently drop evidence needed for diagnostics.
- Latest valid position per device, separate from latest heartbeat/last-seen.
- Historical query by device and time interval, pagination or sampling where appropriate.
- Organization-level authorization and efficient fleet-level latest-position queries.
- Stream new location events to active authorized browsers (WebSocket/SSE, with reconnect snapshot).
- Background event evaluation and report generation as complexity grows.

### Processing integrity

- Unsent samples can arrive **late and out of order**; do not overwrite a newer `latest_position` with an older recorded position.
- Deduplicate at the database layer using a durable unique key such as `(device_id, sample_id)`.
- Preserve `recorded_at` and `received_at` separately.
- Range checks: latitude [-90, 90], longitude [-180, 180], plausible timestamps, finite numeric values, defensible speed/heading checks.
- Flag suspicious GPS jumps and poor quality; keep a distinction between raw points and points accepted for analytics.
- Compute time-based metrics from **capture timestamps**, not the order of upload.
- Define configurable thresholds for device stale/offline, stops, trips, movement and geofence entry/exit.

### Suggested technology (initial, subject to repository constraints)

| Component             | Proposal                                             | Notes                                                                                |
| --------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Firmware              | PlatformIO + Arduino/C++, or ESP-IDF                 | Hardware abstraction by interface                                                    |
| Backend               | Python **FastAPI**                             | REST + WebSockets + background integration                                           |
| Relational/spatial DB | **PostgreSQL + PostGIS**                       | Recommended for growing spatial queries; existing MySQL acceptable for a smaller MVP |
| Frontend              | **React**                                      | Responsive dashboard                                                                 |
| Map                   | **Leaflet**                                    | Select a map tile provider with appropriate production usage rights and capacity     |
| Background jobs       | In-process initially; worker + queue when needed     | Avoid heavyweight infrastructure prematurely                                         |
| Cache/pub-sub         | Optional Redis as scale demands                      | Not required for the first prototype                                                 |
| Device transport      | **HTTPS POST**, MQTT over TLS optionally later | Keep server contract versioned                                                       |
| Deploy                | **Docker Compose** initially                   | Containerize backend, web, database, migrations                                      |
| Storage/archive       | DB initially; object storage later                   | Retention, backup, optional cold archive                                             |

**Scaling guidance:** Index tenant/device/time queries; consider range partitioning by time, spatial indexes, summaries/downsampled views for long time ranges, and lifecycle/retention jobs. Load test before adding unnecessary distributed services.

---

## 7. Domain Data Model

Make the model useful for other asset-tracking applications, not only trucking.

| Entity/table             | Main fields / purpose                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `organizations`        | Tenant/company, name, status, settings                                                                                        |
| `users`                | Identity, enabled state, login metadata                                                                                       |
| `organization_members` | User <-> organization role and permissions                                                                                    |
| `fleets`               | Company-specific groups of assets/vehicles                                                                                    |
| `assets`               | Generic tracked object: type (`vehicle`, `equipment`, `container`, etc.), name, metadata, org/fleet                     |
| `vehicles`             | Vehicle-specific extension: registration/plate, type, optional capacity; **not a replacement for generic assets**       |
| `drivers`              | Optional driver roster; personal information handled with access control                                                      |
| `driver_assignments`   | Driver-to-vehicle/asset relationship valid for a time interval                                                                |
| `devices`              | Hardware ID, firmware, connectivity mode, provisioning/auth reference, status                                                 |
| `device_assignments`   | Device-to-asset mapping with `valid_from`/`valid_to`; avoids attributing old trips to a reassigned vehicle                |
| `positions`            | Raw valid/flagged GNSS records: device, coordinates, capture/arrival times, speed, heading, quality, tenant linkage as needed |
| `device_latest`        | Most recent valid position, quality/status, last recorded/received timestamps                                                 |
| `device_heartbeats`    | Device connectivity and power state even when GNSS fix is missing                                                             |
| `trips`                | Start/end, distance, movement duration, asset/device association, processing version                                          |
| `stops`                | Stop start/end, centroid, duration, classification                                                                            |
| `geofences`            | Organization-owned circles/polygons and policies                                                                              |
| `geofence_events`      | Enter/exit event, asset, event time, evaluated rule/version                                                                   |
| `alerts`               | Rule, severity, status, asset, event timestamp, acknowledgement                                                               |
| `audit_logs`           | Security and administrative actions                                                                                           |

**Important modeling rules:**

- Store event timestamps in UTC; convert to local timezone only for UI.
- Use `organization_id` as an enforced access boundary where appropriate; avoid trusting unverified tenant IDs in incoming telemetry.
- Vehicle-to-device assignments change over time; reporting must use the correct assignment for the event time.
- Maintain migration history and explicit delete/retention policy.
- Keep calculated data (trips, stops, alerts) traceable back to source positions and the algorithm configuration used.

---

## 8. API Design (Proposed, Not Yet Implemented)

### Device ingestion endpoints

```http
POST /api/v1/telemetry
POST /api/v1/telemetry/batch
POST /api/v1/devices/heartbeat
```

### Web and fleet endpoints

```http
GET  /api/v1/me
GET  /api/v1/organizations
GET  /api/v1/organizations/{org_id}/overview
GET  /api/v1/assets
POST /api/v1/assets
GET  /api/v1/assets/{asset_id}
GET  /api/v1/assets/{asset_id}/latest
GET  /api/v1/assets/{asset_id}/positions?from=...&to=...
GET  /api/v1/assets/{asset_id}/trips?from=...&to=...
GET  /api/v1/fleets
GET  /api/v1/fleets/{fleet_id}/latest
GET  /api/v1/devices
GET  /api/v1/geofences
GET  /api/v1/alerts
GET  /api/v1/reports/fleet?from=...&to=...
WS   /api/v1/ws/locations
GET  /api/v1/health
```

### Integration endpoints (later)

```http
GET  /api/v1/exports/positions
GET  /api/v1/exports/trips
POST /api/v1/webhooks
```

All human-facing endpoints require authentication and authorization. Fleet/asset/device IDs must be checked against organization membership. Avoid exposing large unbounded historical queries; require date ranges and pagination/downsampling where appropriate. Define consistent error responses and OpenAPI docs.

---

## 9. Web Platform: Navigation and Screens

### Main navigation (suggested)

1. **Overview:** Fleet KPIs, online/offline devices, moving/stopped counts, current alerts.
2. **Live Map:** Multiple vehicles/assets, clustering, search and fleet filters, click for telemetry detail.
3. **History & Playback:** Select asset/time period, show measured route, timestamped replay and known signal gaps.
4. **Trips & Stops:** List trips, distance/time/duration, stop events, route metrics, export.
5. **Fleet Management:** Fleets, vehicles/assets, driver records, device-asset assignment.
6. **Geofences & Alerts:** Define allowed/restricted areas, alert policies, event histories.
7. **Reports & Analytics:** Organization/fleet/vehicle summaries by date range.
8. **Devices:** Enrollment, connectivity, health, firmware and last check-in.
9. **Administration:** Organization, users, roles, retention, API access, audit information.

### Live map behavior

- Show last confirmed position, time of fix, speed, heading, and connectivity information.
- Distinguish **moving/stopped** (inferred from position policy) and **online/stale/offline** (based on report freshness).
- Do **not** label a stale last-known position as a live reading.
- Initial map load obtains a latest-position snapshot, then subscribes to realtime deltas; recover after disconnect.
- Show groups/cluster markers when many assets are in the same area.
- Dashboard should work on desktop and mobile browsers.
- Track and show network/GNSS quality where available.

### History behavior

- User selects vehicle/asset and UTC-backed date-time range.
- Show points or routes chronologically, with timestamps and playback control.
- Long GNSS outages are not represented as known routes; use dashed connections or separate segments.
- Support CSV and GeoJSON first; GPX can be added later.
- Handle large date ranges efficiently through bounds, pagination, downsampling, or precomputed geometry.

---

## 10. Fleet Management and Analytics Use Cases

### 10.1 Transportation company example

A fleet manager operating 100 trucks should be able to:

- See the location and last update of every equipped vehicle.
- Search by plate, driver assignment, fleet, and vehicle status.
- Review which trucks are traveling and which have been stationary.
- Check a vehicle's route during a selected shift or day.
- Compare travel distance, trip duration, stop time and trip counts across assets.
- Detect arrival at/departure from a configured depot or customer geofence.
- Get an alert when a device is offline, loses power (if detectable), exits a permitted area, or stays stationary beyond a threshold.
- Export daily, weekly, or monthly fleet summaries.
- Access authorized data from another transport-management system using APIs.

### 10.2 Useful initial analytics

| Metric                           | Calculation concept                                    | Data limitations                                                    |
| -------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------- |
| Traveled distance                | Sum plausible consecutive GNSS segment distances       | Gaps and noisy fixes can distort totals; optionally map-match later |
| Trip count                       | Configurable time/movement threshold trip segmentation | GPS-only trip definition is heuristic                               |
| Moving duration                  | Intervals classified as moving based on speed/position | Dependent on sampling, threshold, and quality                       |
| Stop duration                    | Sustained low movement in a radius over minimum time   | Does not prove engine-off or idling                                 |
| Average / maximum observed speed | GNSS speed over accepted trip points                   | GPS quality and sampling affect measurements                        |
| Vehicle utilization              | Active-travel time versus chosen available time        | Requires agreed operational definition                              |
| Geofence enter/exit              | Compare geometry against positions with hysteresis     | Delays possible with low update rate / GNSS errors                  |
| Route deviation                  | Compare measured path with a designated corridor       | Requires a planned route/corridor definition                        |
| Offline / low-battery events     | Device heartbeat/status and thresholds                 | Requires reliable device metadata                                   |

**Do not overclaim what GPS alone can measure:**

- **Engine idling** requires ignition/engine signal or equivalent additional evidence; GPS stationary time is not necessarily idling.
- **Fuel consumption** requires fuel/CAN/OBD or another verified data source; it cannot be derived reliably from location alone.
- **Driving behavior / harsh braking** requires appropriate high-rate motion or acceleration signals and validation; 5-second GPS updates alone are generally insufficient.
- **Speeding versus legal limit** needs a trustworthy road speed-limit source, appropriate map matching, and uncertainty handling.
- **Driver identity** requires an explicit assignment/login/identification method, not location alone.
- **ETA / route optimization** require routing/traffic data and a separate implementation; not an automatic result of recording GPS points.

### 10.3 Future applications beyond vehicles

- Rental and construction-equipment location tracking.
- Logistics container or trailer tracking.
- Portable high-value asset movement history.
- Field-service technician dispatch (with lawful, appropriate tracking and access controls).
- Industrial equipment monitoring integrated with other telemetry.
- Customer dashboards or industry-specific applications using the core API.

---

## 11. Alerts and Geofencing

Start with a simple configurable rules engine:

- GNSS device offline / reporting gap.
- Battery low or supply interruption (where hardware reports reliably).
- Asset enters/exits a circle or polygon.
- Asset leaves an authorized operating area.
- Asset remains stationary beyond a configurable duration.
- Device location suddenly jumps implausibly (diagnostic quality event).

Rules must be evaluated using timestamps and GPS confidence, with debounce/hysteresis to avoid repeated alerts due to border jitter. Store event history, owner organization, threshold settings, last evaluation state, and acknowledgement information. In-app alerts first; email/SMS/Telegram/WhatsApp notifications can be modular future integrations.

---

## 12. Security, Privacy, and Operational Controls

- HTTPS/TLS for device communication, browser sessions and integrations.
- A unique **credential per device**; rotate/revoke on loss or compromise. Store only safe secret hashes/references as appropriate.
- Human user authentication, strong organization-scoped RBAC, session management and account audit trail.
- Ensure an organization's user cannot query another organization's devices/assets by changing IDs in URLs.
- Validate every upload and restrict max batch size, date ranges and query response sizes.
- Protect precise movement history as sensitive operational/personal information. Define who is tracked, legitimate purpose, consent/notice where required, retention periods, access logging, and deletion procedures.
- Backup/restore procedure and monitored storage capacity; periodic integrity checks.
- Secrets in environment variables or secret manager, never committed to source control.
- Map tile licensing, rate limits and commercial terms should be reviewed before production deployment.
- For automotive installations, use appropriate electrical protection, mounting, heat handling, and safe battery engineering.

---

## 13. Reliability, Observability, and Scaling

### Suggested service health metrics

- Ingestion requests, accepted/rejected/duplicate counts and reasons.
- Device last-seen time, last valid GNSS time, offline queue depth (if reported), firmware.
- Ingestion latency: `received_at - recorded_at` (separate healthy realtime transmissions from delayed offline replay).
- Database size, daily position count, query latency, retention job state.
- WebSocket client connections and live event lag.
- Trip/geofence/background processing failures and queue backlogs.
- Uptime, server errors, backups and storage utilization.

### Performance strategy

1. Keep a materialized `device_latest` table for fleet map reads.
2. Index by `(device_id, recorded_at)` and tenant queries; use PostGIS where geometry helps.
3. Restrict history requests and downsample long traces for UI rendering.
4. Batch offline replay and use idempotent ingestion.
5. Use time-based table partitioning/retention when scale demands it.
6. Offload long-running analytics to background workers once real workload requires it.
7. Avoid broadcasting every raw point to every user; subscribe users to their authorized organization/fleet/device scopes.
8. Load-test with a simulated 100-device fleet, then 1,000 devices, to determine infrastructure needs.

---

## 14. Development Roadmap

### Milestone A — Core software platform (build before hardware arrives)

- Define telemetry JSON schema and domain entities.
- Develop FastAPI + PostgreSQL/PostGIS with Docker Compose and migrations.
- Build per-device authenticated ingestion, deduplication, offline replay, latest positions and history endpoints.
- Create a realistic Python GPS fleet simulator with unique devices, synthetic trajectories, late arrivals and network-loss cases.
- Create React/Leaflet live map with device list, live/stale/offline indicators and individual route playback.
- Implement minimal organization scoping even if only one seeded company exists initially.
- Add tests and developer setup docs.

**Acceptance:** Run the complete software workflow locally without physical devices; simulate multiple vehicles and retrieve correct latest positions and historical routes.

### Milestone B — First physical tracker

- Wire **XIAO ESP32S3 + L76K GNSS** with verified vendor pinout and antenna arrangement.
- Read validated GNSS positions at approximately 1 Hz and report every 5 seconds via Wi-Fi/HTTPS.
- Test mobile hotspot connectivity in a car and proper timestamping.
- Add bounded persistent queue for offline periods, deduplication/replay and status messages.
- Test positioning near the windshield, dropouts in garages/tunnels and dashboard temperature.

**Acceptance:** Physical tracker and simulator share the same backend schema; no fictitious positions during GNSS loss; after network recovery queued points return with their original acquisition timestamps.

### Milestone C — Fleet management MVP

- Organization users/roles; fleets, assets, vehicles, and time-bound device assignments.
- Multi-vehicle map, fleet filters and search; trip/stop rules; daily summary views.
- Geofences and offline alerts; CSV/GeoJSON export.
- Initial 100-device simulation/load test and authorization tests.

**Acceptance:** A demo transport company with many vehicles can monitor live positions, review history, generate basic fleet metrics, and keep data segregated from a separate demo company.

### Milestone D — Cellular tracker and operational deployment

- Evaluate **4G LTE + SIM**, ideally with integrated GNSS, and verify actual network bands.
- Add secure provisioning, connectivity diagnostics, watchdog and operational logging.
- Harden deployment: domain, HTTPS, backups, monitoring, alerting, retention and audit controls.
- Trial in several real vehicles over representative routes and connectivity conditions.

### Milestone E — Compact hardware, battery options, and product expansion

- Measure full-system power and GNSS/RF reliability; design smaller custom PCB and enclosure.
- Add protected automotive wired power and optional safe battery-powered design.
- Add optional OTA/config management and documented external API/webhooks.
- Expand analytics and industry-specific applications based on actual field evidence.

---

## 15. Validation and Acceptance Criteria

The following are recommended checks; finalize numeric SLAs after prototype measurements:

1. Device uploads cannot impersonate another device.
2. Retried telemetry does not create duplicate stored positions.
3. Older delayed data never moves the displayed latest position backward in time.
4. Live map distinguishes valid/live/stale/offline states correctly.
5. Historical route is ordered by **recorded time** and marks long GNSS gaps honestly.
6. Data from Company A is not accessible to Company B using API, WebSocket, or reports.
7. Assignment history correctly attributes old points to the asset that held the tracker at the time.
8. GPS simulator supports 1, 10, and 100 concurrent device scenarios; record actual throughput/latency and failures.
9. Fleet reports reconcile to stored source points and document their calculations.
10. Vehicle test compares tracked positions to reference data; log GNSS quality and time to fix.
11. Offline queue resumes after network reconnect and (where feasible) power cycle without silently losing already acknowledged/unacknowledged records.
12. Dashboard works on mobile and desktop; history queries remain bounded and usable.
13. Secure default deployment includes TLS, backup plan, error logs, and credential rotation procedure.
14. The system can accommodate new trackers/assets without rewriting the core architecture.

---

## 16. Recommended Repository Layout

```text
gps-tracking-platform/
├── README.md
├── docs/
│   ├── PROJECT_SPEC.md                # this document
│   ├── architecture.md
│   ├── telemetry-contract.md
│   ├── data-model.md
│   ├── api.md
│   ├── security-and-tenancy.md
│   ├── hardware-bom-and-wiring.md
│   └── test-plan.md
├── backend/
│   ├── app/
│   │   ├── api/                       # routes by domain
│   │   ├── auth/                      # human and device auth
│   │   ├── models/                    # ORM entities
│   │   ├── schemas/                   # request/response contracts
│   │   ├── services/                  # location, trips, geofence etc.
│   │   ├── jobs/                      # optional background jobs
│   │   ├── db/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/                     # overview, map, history, fleet...
│   │   ├── components/
│   │   ├── features/
│   │   ├── services/
│   │   └── hooks/
│   └── package.json
├── firmware/
│   └── xiao-esp32s3-l76k/
│       ├── platformio.ini
│       ├── include/
│       └── src/
├── simulator/
│   ├── fleet_simulator.py
│   └── sample_routes/
├── infrastructure/
│   ├── docker-compose.yml
│   └── .env.example
└── scripts/
    └── seed_demo_company.py
```

The structure is proposed. Codex should adapt to any existing repository rather than overwrite unrelated work.

---

## 17. Codex Implementation Instructions

### Operating rules for Codex

- Treat this document as the current source of truth for product scope.
- Build the **platform foundation first**, using simulated GPS streams while the physical device is being built.
- Start with a **modular monolith**, not microservices. Isolate domains in code so they can be separated later if required.
- Use a versioned telemetry contract shared by all device variants.
- Implement basic multi-tenancy from the beginning, including API and WebSocket authorization.
- Use migrations, explicit schemas, UTC times, tests, useful error messages, and documented configuration.
- Do not hardcode secret credentials or device keys in source code.
- Do not invent hardware wiring or GNSS pin assignments; confirm from purchased board revisions.
- Do not implement speculative AI features before collected data and analytical definitions exist.
- Be explicit about prototype assumptions, known limitations and unsupported measurements.

### First implementation backlog

1. Scaffold local Docker Compose environment and dependencies.
2. Model organizations, users/memberships, devices, assets, assignments, positions, and latest state.
3. Create migrations, seed company, several vehicles/assets, and device identities.
4. Implement device-key-authenticated `/api/v1/telemetry` and batch ingestion with idempotency and tests.
5. Implement `/api/v1/assets`, fleet latest positions, history endpoints and authorization checks.
6. Implement WebSocket live updates scoped to allowed companies/assets.
7. Create realistic simulator with 10 and 100 GPS devices, routes, stops, bad fix, late replay, and network outages.
8. Build React/Leaflet map: fleet list, selection, status, map markers, latest details.
9. Build date-range route history and playback with marked GPS gaps.
10. Add integration tests for cross-tenant isolation, deduplication, delayed telemetry, ordering, and basic UI flows.
11. Add README, `.env.example`, API documentation, and reproducible local run commands.
12. Only after end-to-end simulator validation, implement XIAO ESP32S3 + L76K firmware.

### Copy/paste prompt for Codex

```text
Read docs/PROJECT_SPEC.md completely. This project is not merely an ESP32 GPS tracker: it is a reusable multi-tenant GPS Tracking & Fleet Intelligence Platform with hardware as one data source.

First implement Milestone A as a locally runnable, end-to-end software MVP. Use FastAPI, PostgreSQL/PostGIS, React + Leaflet, Docker Compose, migrations, and a Python multi-device GPS simulator, unless the existing repository already has equivalent choices. Build a modular monolith with organization-scoped auth, per-device authenticated and idempotent telemetry ingestion, current/latest locations, recorded-at history, a live map, and route playback. Provide test data for a fleet of vehicles and test cross-tenant isolation, duplicate replay, GNSS gaps and out-of-order uploads.

Keep the data model general enough for vehicles and other tracked assets. Document schemas, endpoints, setup commands, tests, security assumptions, and unresolved issues. Do not start with PCB design, LTE hardware, complex microservices, advanced AI, or fuel/idling analytics unsupported by GPS alone. Show a short implementation plan, then implement and test the first vertical slice.
```

---

## 18. Decisions, Assumptions, and Future Questions

### Confirmed through discussion

- The **final product is a complete platform**, not only a standalone GPS gadget.
- It must receive and store location data from many devices, show live locations and historical tracks, and enable multiple downstream applications.
- A **transportation company with many vehicles** is a key example and should drive the first business application.
- Hardware supports Wi-Fi and SIM/4G alternatives, plus wired and battery-powered versions eventually.
- Prototype with modules first; optimize the final circuit and enclosure only after reliable operation.
- The first preferred tracker uses **XIAO ESP32S3 + L76K**, Wi-Fi and USB power.
- The dashboard tracker can be small and visible near a vehicle windshield.
- Compact design is important, but accurate GNSS reception and reliable communications take precedence.

### Design proposals, not yet final decisions

- FastAPI + PostgreSQL/PostGIS + React/Leaflet + Docker Compose.
- Hosted multi-tenant organization/workspace model (a single-company self-hosted edition could also be supported later).
- First commercial use case: vehicle/fleet management with trip/stop/geofence analytics.
- Reporting intervals, hardware dimensions, roles, thresholds, data retention and billing model.
- Exact LTE modem and antennas; final compact PCB and product enclosure.

### Later product decisions to resolve with evidence

- Target customers and deployment geography; self-hosted versus SaaS or both.
- Expected fleet size (10, 100, 1,000, or more devices) and retention period.
- Which functions are essential for the first paying customer: live monitoring, dispatch, geofence, reports, or integration.
- Vehicle power source: accessory USB, ACC 12/24 V, or always-on supply.
- How company operators handle driver assignments and privacy obligations.
- Integration with other business software and hardware input sources such as OBD/CAN.

---

## 19. Reference Documents to Verify During Implementation

Before hardware purchases and production deployments, confirm the precise part revisions and current official documentation for:

- Seeed Studio XIAO ESP32S3 and XIAO ESP32C3 documentation.
- Seeed L76K GNSS / XIAO expansion documentation.
- Selected LTE Cat-1/GNSS modem or evaluation board (including supported frequencies).
- Espressif ESP32-S3, Arduino-ESP32 / ESP-IDF, and PlatformIO.
- FastAPI, PostgreSQL, PostGIS, React and Leaflet documentation.
- Applicable privacy/telecommunications, mapping/tile licensing and vehicle-electronics requirements for the deployment market.

**Overall guiding principle:** **Build one reliable, extensible location-data platform. Feed it with compact tracking devices. Add industry-specific intelligence above the core, without rebuilding the foundation.**
