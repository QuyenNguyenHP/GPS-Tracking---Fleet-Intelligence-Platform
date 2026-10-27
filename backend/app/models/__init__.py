from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Membership(Base):
    __tablename__ = "organization_members"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(30), default="viewer")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), default="vehicle")


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Assignment(Base):
    __tablename__ = "device_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Position(Base):
    """All accepted telemetry, including no-fix heartbeats, for replay and diagnostics."""
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("device_id", "sequence_number"),
                      Index("ix_positions_asset_time", "organization_id", "asset_id", "recorded_at", "id"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    sequence_number: Mapped[int] = mapped_column(BigInteger)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fix_valid: Mapped[bool] = mapped_column(Boolean)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)


class DeviceLatest(Base):
    __tablename__ = "device_latest"
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
