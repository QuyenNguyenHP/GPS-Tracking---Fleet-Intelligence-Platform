"""Local account recovery. Run from backend so the default database is backend/fleet.db."""
import argparse
from getpass import getpass
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import delete, select
from app.auth import digest
from app.auth.passwords import hash_password
from app.db import SessionLocal
from app.models import LoginSession, User


def reset_password(username, password):
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must contain 8-128 characters")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip().lower()).with_for_update())
        if not user:
            raise ValueError("Account not found. Check your database connection and username.")
        user.password_hash = hash_password(password)
        user.token_hash = digest(secrets.token_urlsafe(32))
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()
    try:
        password = getpass("New password (8-128 characters): ")
        if password != getpass("Confirm new password: "):
            raise ValueError("Passwords do not match")
        reset_password(args.username, password)
        print("Password updated and existing sessions revoked. Account role and enabled state unchanged.")
        print("Sign in with your new password; the initial password in the demo file is no longer applicable.")
    except (ValueError, EOFError, KeyboardInterrupt) as exc:
        raise SystemExit(str(exc) or "Cancelled")
