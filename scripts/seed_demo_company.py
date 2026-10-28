"""Run after migrations. Re-running keeps credentials and existing telemetry intact."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.auth import digest
from app.auth.passwords import hash_password
from app.db import SessionLocal
from app.models import Asset, Assignment, Device, Membership, Organization, User


def seed(count, output):
    if not 1 <= count <= 100:
        raise ValueError("Choose 1 to 100 devices")
    if output.exists():
        credentials = json.loads(output.read_text())
    else:
        credentials = {"organizations": []}
    with SessionLocal() as db:
        for slug, name, size in [("demo", "Meridian Logistics", count), ("other", "Harbor Equipment", 1)]:
            entry = next((o for o in credentials["organizations"] if o["id"] == slug), None)
            if not entry:
                if db.get(Organization, slug):
                    raise RuntimeError("Organization exists but credential file is missing; refusing to rotate silently")
                entry = {"id": slug, "name": name, "operator_token": secrets.token_urlsafe(32), "devices": []}
                credentials["organizations"].append(entry)
            if not db.get(Organization, slug):
                db.add(Organization(id=slug, name=name))
                db.add(User(id=slug + "-operator", name=name + " operator", token_hash=digest(entry["operator_token"])))
                db.flush()
                db.add(Membership(user_id=slug + "-operator", organization_id=slug, role="viewer"))
            account_id = slug + "-account"
            if not db.get(User, account_id):
                login = entry.setdefault("account", {
                    "username": "admin" if slug == "demo" else "other.viewer",
                    "password": "admin123" if slug == "demo" else secrets.token_urlsafe(18),
                })
                db.add(User(id=account_id, name="Platform Administrator" if slug == "demo" else "Harbor Viewer",
                            username=login["username"], password_hash=hash_password(login["password"]),
                            token_hash=digest(secrets.token_urlsafe(32)), is_platform_admin=slug == "demo"))
                db.flush()
                db.add(Membership(user_id=account_id, organization_id=slug, role="viewer"))
            for i in range(size):
                device_id, asset_id = f"{slug}-GPS-{i + 1:03}", f"{slug}-asset-{i + 1:03}"
                saved = next((d for d in entry["devices"] if d["device_id"] == device_id), None)
                if not saved:
                    saved = {"device_id": device_id, "asset_id": asset_id, "token": secrets.token_urlsafe(32)}
                    entry["devices"].append(saved)
                if not db.get(Device, device_id):
                    db.add(Asset(id=asset_id, organization_id=slug, name=f"Vehicle {i + 1:03}", kind="vehicle"))
                    db.add(Device(id=device_id, organization_id=slug, token_hash=digest(saved["token"])))
                    db.flush()
                    db.add(Assignment(device_id=device_id, asset_id=asset_id,
                                      valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc)))
        output.parent.mkdir(parents=True, exist_ok=True)
        # Write credentials before committing so a filesystem failure cannot strand new keys.
        temp = output.with_suffix(".tmp")
        temp.write_text(json.dumps(credentials, indent=2))
        temp.chmod(0o600)
        temp.replace(output)
        db.commit()
    print(f"Seeded two organizations. Private credentials: {output}")
    print("Account login: admin. Initial password is in organizations[0].account.password.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("infrastructure/demo-credentials.json"))
    args = parser.parse_args()
    seed(args.devices, args.output)
