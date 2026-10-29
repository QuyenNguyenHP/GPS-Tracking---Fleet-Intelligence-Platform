from sqlalchemy import select

from app.db import utc, utcnow
from app.models import Asset, Device, DeviceLatest, Position


def position_json(p):
    return {"id": p.id, "device_id": p.device_id, "asset_id": p.asset_id,
            "sequence_number": p.sequence_number, "recorded_at": utc(p.recorded_at).isoformat(),
            "received_at": utc(p.received_at).isoformat(), **p.payload["location"],
            "status": p.payload["status"]}


def latest_snapshot(db, org):
    rows = db.execute(select(Device, Position, Asset).outerjoin(DeviceLatest, DeviceLatest.device_id == Device.id)
        .outerjoin(Position, Position.id == DeviceLatest.position_id)
        .outerjoin(Asset, Asset.id == Position.asset_id)
        .where(Device.organization_id == org, Device.enabled.is_(True)).order_by(Device.id)).all()
    now = utcnow()
    result = []
    for device, position, asset in rows:
        seen_age = (now - utc(device.last_seen_at)).total_seconds() if device.last_seen_at else float("inf")
        fix_age = (now - utc(position.recorded_at)).total_seconds() if position else float("inf")
        state = "offline" if seen_age > 120 else "stale" if fix_age > 30 or seen_age > 30 else "live"
        result.append({"device_id": device.id, "enabled": device.enabled,
                       "asset_name": asset.name if asset else None,
                       "state": state, "last_seen_at": utc(device.last_seen_at).isoformat() if device.last_seen_at else None,
                       "position": position_json(position) if position else None})
    return {"type": "snapshot", "server_time": now.isoformat(), "devices": result}
