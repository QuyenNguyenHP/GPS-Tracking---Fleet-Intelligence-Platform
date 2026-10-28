# Milestone A data model

| Entity | Purpose |
|---|---|
| organizations | Company boundary |
| users / organization_members | Hashed operator token, enabled flag, allowed company and initial viewer role |
| login_sessions | Hashed session token, user reference and expiry; logout/reset/disable revokes sessions |
| assets | Company-owned generic tracked item with kind and name |
| devices | Unique hardware identity, company, credential hash, enabled flag and last-seen |
| device_assignments | Asset/device association with inclusive start and exclusive end |
| positions | Immutable accepted telemetry, including no-fix heartbeats, raw normalized payload, acquisition/receipt times and assignment at acquisition |
| device_latest | Pointer to the newest valid position per device |

Unique `(device_id, sequence_number)` prevents duplicate writes. The `(organization_id, asset_id, recorded_at, id)` index supports ordered history pagination. All public reads are membership-scoped. Assignment lookup also checks asset ownership, and ingestion chooses the company from device credentials rather than the caller.

Assignments are seeded and not editable through this milestone's API. Future assignment administration must enforce non-overlapping intervals, same-company references and backfill/reconciliation rules. Never transfer a device between organizations by editing its organization ID; provision a new identity to preserve historical ownership. Fleet groups, vehicle-specific details, drivers, trips and geofences are reserved for Milestone C.

No-fix heartbeats share the event table for deduplication and route-gap evidence. A separate heartbeat partition can be introduced when volume measurements justify it. No retention cleanup runs automatically in this prototype.

Migration `0002` adds unique normalized usernames, salted password hashes, a platform-admin flag, organization enabled state and login sessions. Old operator identities retain nullable username/password fields for API compatibility. Platform-admin status is separate from organization memberships.
