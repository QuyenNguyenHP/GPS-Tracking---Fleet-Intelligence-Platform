import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, utcnow
from app.models import Device, LoginSession, Membership, Organization, User


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def bearer(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Bearer credential required")
    return token


def device_auth(token: str = Depends(bearer), db: Session = Depends(get_db)):
    device = db.scalar(select(Device).join(Organization).where(Device.token_hash == digest(token),
        Device.enabled.is_(True), Organization.enabled.is_(True)))
    if not device:
        raise HTTPException(401, "Invalid or revoked device credential")
    return device


def resolve_user(token, db, allow_legacy=False):
    user = db.scalar(select(User).join(LoginSession).where(
        LoginSession.token_hash == digest(token), LoginSession.expires_at > utcnow(), User.enabled.is_(True)))
    if not user and allow_legacy:
        # Existing demo read-only API integrations keep working. Never grants admin access.
        user = db.scalar(select(User).where(User.token_hash == digest(token), User.enabled.is_(True)))
    if not user:
        raise HTTPException(401, "Session expired or invalid credential. Please sign in.")
    return user


def current_user(token: str = Depends(bearer), db: Session = Depends(get_db)):
    return resolve_user(token, db)


def platform_admin(user: User = Depends(current_user)):
    if not user.is_platform_admin:
        raise HTTPException(403, "Platform administrator access required")
    return user


def user_scope(token, organization_id, db):
    user = resolve_user(token, db, allow_legacy=True)
    membership = db.get(Membership, (user.id, organization_id))
    organization = db.get(Organization, organization_id)
    if not membership or not organization or not organization.enabled:
        raise HTTPException(403, "Organization access denied")
    return organization_id


def organization_auth(token: str = Depends(bearer), x_organization_id: str = Header(default=""),
                      db: Session = Depends(get_db)):
    return user_scope(token, x_organization_id, db)
