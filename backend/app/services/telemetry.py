from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db import utcnow
from app.models import Asset, Assignment, Device, DeviceLatest, Position


def ingest(db, device, samples):
    if any(s.device_id != device.id for s in samples):
        raise HTTPException(403, "Payload device_id must match authenticated identity")
    # Serialize a device's writes in PostgreSQL, including concurrent batches.
    db.execute(select(Device).where(Device.id == device.id).with_for_update())
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    accepted, duplicates = [], []
    now = utcnow()
    for sample in samples:
        payload = sample.model_dump(mode="json")
        assignment = db.scalar(select(Assignment).join(Asset).where(
            Assignment.device_id == device.id, Asset.organization_id == device.organization_id,
            Assignment.valid_from <= sample.recorded_at,
            or_(Assignment.valid_to.is_(None), Assignment.valid_to > sample.recorded_at),
        ).order_by(Assignment.valid_from.desc()))
        statement = insert(Position).values(
            organization_id=device.organization_id, device_id=device.id,
            asset_id=assignment.asset_id if assignment else None,
            sequence_number=sample.sequence_number, recorded_at=sample.recorded_at,
            received_at=now, fix_valid=sample.location.fix_valid,
            latitude=sample.location.latitude, longitude=sample.location.longitude, payload=payload,
        ).on_conflict_do_nothing(index_elements=["device_id", "sequence_number"]).returning(Position.id)
        position_id = db.scalar(statement)
        if position_id is None:
            original = db.scalar(select(Position).where(Position.device_id == device.id,
                                                       Position.sequence_number == sample.sequence_number))
            if original.payload != payload:
                raise HTTPException(409, "Sequence number reused with different telemetry; batch rolled back")
            duplicates.append(sample.sequence_number)
            continue
        accepted.append(sample.sequence_number)
        if sample.location.fix_valid:
            latest = insert(DeviceLatest).values(device_id=device.id, position_id=position_id,
                                                  recorded_at=sample.recorded_at)
            db.execute(latest.on_conflict_do_update(index_elements=["device_id"],
                set_={"position_id": position_id, "recorded_at": sample.recorded_at},
                where=DeviceLatest.recorded_at < sample.recorded_at))
    db.execute(update(Device).where(Device.id == device.id).values(last_seen_at=now))
    db.commit()
    return {"accepted": accepted, "duplicates": duplicates}
