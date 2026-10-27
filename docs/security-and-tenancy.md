# Security and tenancy

Local demo credentials are cryptographically random 32-byte URL-safe tokens. Only SHA-256 digests are stored in the database; generated plaintext credentials are kept in the ignored local credential file for demo use. High-entropy tokens permit direct hashing; this is not a password hashing design. Operator tokens and device tokens are separate identities.

Every operator endpoint verifies both enabled user and organization membership. A client-supplied organization never grants access by itself. Ingestion derives the owner and permitted device from the authenticated credential. WebSockets authenticate in the first frame and recheck authorization every snapshot. Browser credentials live only in React memory.

The Compose ports bind to loopback. HTTP is permitted for local development only. Before deployment add TLS, proper operator login with expiring sessions, RBAC administration, credential rotation/revocation tooling, request/connection rate limits, origin checks, monitoring, backups, retention and audit controls. Do not expose this demo directly to the internet.

Disable a user/device to revoke access; replacing its stored token hash rotates its credential. Provisioning/admin APIs are deliberately deferred. Keep generated credential files private; POSIX mode is restricted by the seed script, but Windows ACLs inherit from the project folder and must be managed by its owner.

Precise location history is sensitive. Set organizational access, retention and tracking policies before real tracking. Development map tiles use OpenStreetMap's public endpoint; evaluate provider terms and capacity before deployment. Font and tile requests use external services.
