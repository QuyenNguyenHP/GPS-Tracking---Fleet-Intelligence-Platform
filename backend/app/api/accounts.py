from collections import OrderedDict, deque
from datetime import timedelta
import secrets
from threading import Lock
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import bearer, current_user, digest
from app.auth.passwords import hash_password, verify_password
from app.db import get_db, utcnow
from app.models import LoginSession, Membership, Organization, User

router = APIRouter(prefix="/api/v1/auth", tags=["Accounts"])
login_attempts = OrderedDict()
attempts_lock = Lock()
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


def throttle(key):
    now = time.monotonic()
    with attempts_lock:
        attempts = login_attempts.setdefault(key, deque())
        login_attempts.move_to_end(key)
        while attempts and attempts[0] <= now - 60:
            attempts.popleft()
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many sign-in attempts. Try again in one minute.", headers={"Retry-After": "60"})
        attempts.append(now)
        while len(login_attempts) > 10000:
            login_attempts.popitem(last=False)


def profile(user, db):
    organizations = db.scalars(select(Organization).join(Membership).where(
        Membership.user_id == user.id, Organization.enabled.is_(True)).order_by(Organization.name))
    return {"id": user.id, "username": user.username, "name": user.name,
            "is_platform_admin": user.is_platform_admin,
            "organizations": [{"id": org.id, "name": org.name} for org in organizations]}


@router.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    throttle("ip:" + (request.client.host if request.client else "unknown"))
    throttle("account:" + username)
    user = db.scalar(select(User).where(User.username == username).with_for_update())
    verified = verify_password(body.password, user.password_hash if user and user.password_hash else DUMMY_HASH)
    if not user or not user.enabled or not verified:
        raise HTTPException(401, "Incorrect username or password")
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(hours=8)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, expires_at=expires))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"token": token, "expires_at": expires.isoformat(), "user": profile(user, db)}


@router.get("/me")
def me(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return profile(user, db)


@router.post("/logout")
def logout(token: str = Depends(bearer), db: Session = Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(token)))
    db.commit()
    return {"ok": True}
