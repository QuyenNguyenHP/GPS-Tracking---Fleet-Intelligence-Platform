from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import platform_admin
from app.db import get_db, utc, utcnow
from app.models import Asset, Assignment, Device, DeviceLatest, Organization, Position
from app.services.locations import position_json

router = APIRouter(prefix="/api/v1/admin", tags=["Database explorer"], dependencies=[Depends(platform_admin)])


@router.get('/devices')
def devices(organization_id: str | None = None, db: Session = Depends(get_db)):
    now = utcnow()
    query = select(Device, Organization.name, Asset.name, Position).select_from(Device).join(
        Organization, Organization.id == Device.organization_id).outerjoin(
        Assignment, and_(Assignment.device_id == Device.id, Assignment.valid_from <= now,
                         or_(Assignment.valid_to.is_(None), Assignment.valid_to > now))).outerjoin(
        Asset, Asset.id == Assignment.asset_id).outerjoin(DeviceLatest, DeviceLatest.device_id == Device.id).outerjoin(
        Position, Position.id == DeviceLatest.position_id)
    if organization_id:
        query = query.where(Device.organization_id == organization_id)
    return {"database": "PostgreSQL" if db.bind.dialect.name == 'postgresql' else 'SQLite',
            "demo_fleet_size": 20,
            "devices": [{"id": device.id, "organization_id": device.organization_id, "organization_name": org_name,
                         "asset_name": asset_name, "enabled": device.enabled,
                         "last_seen_at": utc(device.last_seen_at).isoformat() if device.last_seen_at else None,
                         "latest_recorded_at": utc(position.recorded_at).isoformat() if position else None}
                        for device, org_name, asset_name, position in db.execute(query.order_by(Device.id)).all()]}


@router.get('/telemetry')
def telemetry(start: datetime = Query(alias='from'), end: datetime = Query(alias='to'),
              organization_id: str | None = None, device_id: str | None = None,
              fix: Literal['all', 'valid', 'invalid'] = 'all',
              sequence_number: int | None = Query(default=None, ge=0, le=9223372036854775807),
              limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0, le=1000000),
              db: Session = Depends(get_db)):
    if start.tzinfo is None or end.tzinfo is None or end <= start or end - start > timedelta(days=7):
        raise HTTPException(422, 'Use timezone-aware from/to with a range of at most seven days')
    filters = [Position.recorded_at >= start, Position.recorded_at <= end]
    if organization_id:
        filters.append(Position.organization_id == organization_id)
    if device_id:
        filters.append(Position.device_id == device_id)
    if fix != 'all':
        filters.append(Position.fix_valid.is_(fix == 'valid'))
    if sequence_number is not None:
        filters.append(Position.sequence_number == sequence_number)
    total = db.scalar(select(func.count()).select_from(Position).where(*filters))
    rows = db.scalars(select(Position).where(*filters).order_by(Position.recorded_at.desc(), Position.id.desc())
                      .offset(offset).limit(limit)).all()
    return {"total": total, "offset": offset, "limit": limit,
            "next_offset": offset + limit if offset + len(rows) < total else None,
            "queried_at": utcnow().isoformat(),
            "records": [{**position_json(row), "organization_id": row.organization_id,
                         "latency_seconds": round((utc(row.received_at) - utc(row.recorded_at)).total_seconds(), 3),
                         "payload": row.payload} for row in rows]}
