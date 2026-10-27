import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Device, Membership, User


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def bearer(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Bearer credential required")
    return token


def device_auth(token: str = Depends(bearer), db: Session = Depends(get_db)):
    device = db.scalar(select(Device).where(Device.token_hash == digest(token), Device.enabled.is_(True)))
    if not device:
        raise HTTPException(401, "Invalid or revoked device credential")
    return device


def user_scope(token, organization_id, db):
    user = db.scalar(select(User).where(User.token_hash == digest(token), User.enabled.is_(True)))
    if not user:
        raise HTTPException(401, "Invalid operator credential")
    membership = db.get(Membership, (user.id, organization_id))
    if not membership:
        raise HTTPException(403, "Organization access denied")
    return organization_id


def organization_auth(token: str = Depends(bearer), x_organization_id: str = Header(default=""),
                      db: Session = Depends(get_db)):
    return user_scope(token, x_organization_id, db)
