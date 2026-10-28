import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import digest, platform_admin
from app.auth.passwords import hash_password
from app.db import get_db
from app.models import LoginSession, Membership, Organization, User

router = APIRouter(prefix="/api/v1/admin", tags=["Platform administration"], dependencies=[Depends(platform_admin)])


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True


class OrganizationCreate(OrganizationUpdate):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    is_platform_admin: bool = False
    organization_ids: list[str] = Field(max_length=1000)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class UserCreate(UserUpdate):
    username: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._@-]{2,99}$")
    password: str = Field(min_length=8, max_length=128)


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This username or organization ID already exists")


def user_json(user, memberships):
    return {"id": user.id, "name": user.name, "username": user.username,
            "enabled": user.enabled, "is_platform_admin": user.is_platform_admin,
            "organization_ids": memberships}


def organization_json(org):
    return {"id": org.id, "name": org.name, "enabled": org.enabled}


@router.get("/organizations")
def organizations(db: Session = Depends(get_db)):
    return [organization_json(org) for org in db.scalars(select(Organization).order_by(Organization.name))]


@router.post("/organizations", status_code=201)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    org = Organization(**body.model_dump())
    db.add(org)
    commit(db)
    return organization_json(org)


@router.put("/organizations/{organization_id}")
def update_organization(organization_id: str, body: OrganizationUpdate, db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    org.name, org.enabled = body.name, body.enabled
    commit(db)
    return organization_json(org)


@router.get("/users")
def users(db: Session = Depends(get_db)):
    memberships = {}
    for member in db.scalars(select(Membership)):
        memberships.setdefault(member.user_id, []).append(member.organization_id)
    return [user_json(user, memberships.get(user.id, [])) for user in db.scalars(select(User).order_by(User.name))]


def validate_memberships(body, db):
    ids = set(body.organization_ids)
    existing = set(db.scalars(select(Organization.id).where(Organization.id.in_(ids))))
    if ids != existing:
        raise HTTPException(422, "One or more organizations do not exist")
    return sorted(ids)


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    ids = validate_memberships(body, db)
    username = body.username.lower()
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(409, "This username already exists")
    user = User(id=str(uuid4()), username=username, name=body.name, enabled=body.enabled,
                is_platform_admin=body.is_platform_admin, password_hash=hash_password(body.password),
                token_hash=digest(secrets.token_urlsafe(32)))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This username already exists")
    db.add_all([Membership(user_id=user.id, organization_id=org, role="viewer") for org in ids])
    commit(db)
    return user_json(user, ids)


@router.put("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, admin: User = Depends(platform_admin), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(404, "User not found")
    if not user.username and (body.password or body.is_platform_admin):
        raise HTTPException(422, "Legacy API identities cannot become login accounts. Create a new account instead.")
    if user_id == admin.id and (not body.enabled or not body.is_platform_admin):
        raise HTTPException(409, "You cannot disable your own account or remove your own platform-admin role")
    ids = validate_memberships(body, db)
    user.name, user.enabled, user.is_platform_admin = body.name, body.enabled, body.is_platform_admin
    if body.password:
        user.password_hash = hash_password(body.password)
        user.token_hash = digest(secrets.token_urlsafe(32))  # Revoke legacy credentials too.
    if body.password or not body.enabled:
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.execute(delete(Membership).where(Membership.user_id == user.id))
    db.add_all([Membership(user_id=user.id, organization_id=org, role="viewer") for org in ids])
    commit(db)
    return user_json(user, ids)
