# Account login and platform administration

Restart the backend with `python3 app.py` from `backend`. The launcher upgrades the existing database to migration `0002` and seeds account login for the default local SQLite demo. Existing telemetry, device keys and legacy operator identities are retained. No additional backend dependencies are required.

For a custom `DATABASE_URL`, run migrations and provisioning explicitly:

```bash
python3 -m alembic upgrade head
python3 ../scripts/seed_demo_company.py --output ../infrastructure/demo-credentials.json
```

The default local platform account is **admin / admin123**, as requested for development. The seed file records the initial credentials in the `demo` organization's `account` object. The other demo organization has an `other.viewer` account with a generated password. Change the default admin password before deployment. Seeding again does not reset passwords, roles or disabled accounts. After a password reset, the initial password in the seed file is obsolete.

The login screen asks for username and password. Usernames are case-insensitive. Passwords are case-sensitive, 8–128 characters when created/reset. Accounts are not self-registered; a platform administrator creates them.

If the initial password no longer matches and you have forgotten the current password, recover the account locally from the `backend` directory:

```bash
python3 ../scripts/reset_account_password.py admin
```

Enter and confirm a new password when prompted; input is hidden. This revokes existing sessions without changing account roles, membership or enabled state. It does not update the old password in the seed file. Use the same `DATABASE_URL` as the backend if using a custom database. Do not run the server or recovery command with sudo.

If the screen remains on “Signing in…”, API requests now time out after 15 seconds and restore the form with an error. Check both `http://127.0.0.1:8000/api/v1/health` and `http://127.0.0.1:5173/api/v1/health` from WSL to distinguish backend errors from frontend proxy/connectivity problems. Keep both development terminals in the same WSL environment.

Platform administrators open the admin page after login and can:

- Create organizations, rename them and enable/disable them.
- Create accounts, edit display names and enable/disable accounts.
- Grant/revoke platform-admin access for other accounts.
- Assign each account to one or more organization workspaces, or none.
- Set a new account password; all existing sessions for that account are revoked.
- Search organizations/users and switch back to the fleet workspace.

An administrator cannot disable or demote their own account. Disabling an organization blocks its device ingestion and workspace access, while retaining stored data. Regular viewers cannot call any platform-admin endpoint. Platform-admin status authorizes global administration but does not implicitly authorize fleet history; map/history still require explicit organization membership. There is no hard-delete action.

Legacy operator identities are shown explicitly and remain usable by existing read-only API integrations. They cannot sign in, be assigned a password or obtain platform-admin access; create a named account instead. Their enabled state and memberships can be managed normally.

## Sessions and password storage

Passwords use independently salted PBKDF2-HMAC-SHA256 with 600,000 iterations (see [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)). The database stores only password hashes and session-token hashes. Sessions are random tokens expiring after eight hours, held only in browser memory; reloading the page requires signing in again. Signing out revokes the server session. Disabled users, removed memberships and disabled organizations are checked on every request and each WebSocket snapshot.

Login is limited to ten attempts per minute per client address and per username, in a bounded process-local cache. For multi-worker/production deployments use a shared limiter and trusted reverse-proxy configuration. TLS, audit logs, MFA, self-service recovery and finer organization roles remain deployment/future work. The initial password exists in the private seed credential file for local onboarding only.

## API

| Endpoint | Access |
|---|---|
| `POST /api/v1/auth/login` | Username/password; returns session token, expiry and profile |
| `GET /api/v1/auth/me` | Active session |
| `POST /api/v1/auth/logout` | Revokes supplied session |
| `GET/POST /api/v1/admin/organizations` | Platform admin |
| `PUT /api/v1/admin/organizations/{id}` | Platform admin; name and enabled state |
| `GET/POST /api/v1/admin/users` | Platform admin |
| `PUT /api/v1/admin/users/{id}` | Platform admin; full editable account fields, optional new password |

Admin requests require the login session bearer token. Device and legacy operator tokens are rejected. Account APIs never return password hashes, passwords or device credentials. Lists are intended for the local prototype; large-platform pagination is not yet implemented.
