import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import device_auth, organization_auth, user_scope
from app.db import get_db, SessionLocal, utc
from app.models import Asset, Device, Position
from app.schemas import Batch, Telemetry
from app.services.locations import latest_snapshot, position_json
from app.services.telemetry import ingest

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.post("/telemetry")
def telemetry(sample: Telemetry, device: Device = Depends(device_auth), db: Session = Depends(get_db)):
    return ingest(db, device, [sample])


@router.post("/telemetry/batch")
def batch(body: Batch, device: Device = Depends(device_auth), db: Session = Depends(get_db)):
    return ingest(db, device, body.samples)


@router.get("/assets")
def assets(org: str = Depends(organization_auth), db: Session = Depends(get_db)):
    return [{"id": a.id, "name": a.name, "kind": a.kind} for a in
            db.scalars(select(Asset).where(Asset.organization_id == org).order_by(Asset.id))]


@router.get("/devices/latest")
def latest(org: str = Depends(organization_auth), db: Session = Depends(get_db)):
    return latest_snapshot(db, org)


@router.get("/assets/{asset_id}/positions")
def history(asset_id: str, start: datetime = Query(alias="from"), end: datetime = Query(alias="to"),
            limit: int = Query(default=1000, ge=1, le=5000), offset: int = Query(default=0, ge=0, le=1000000),
            org: str = Depends(organization_auth), db: Session = Depends(get_db)):
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.organization_id == org))
    if not asset:
        raise HTTPException(404, "Asset not found")
    if start.tzinfo is None or end.tzinfo is None or end <= start or end - start > timedelta(days=7):
        raise HTTPException(422, "Use timezone-aware from/to with a range of at most seven days")
    # Include no-fix records: the UI must break the line even for short signal losses.
    points = list(db.scalars(select(Position).where(Position.organization_id == org,
        Position.asset_id == asset_id, Position.recorded_at >= start, Position.recorded_at <= end)
        .order_by(Position.recorded_at, Position.id).offset(offset).limit(limit + 1)))
    return {"points": [position_json(p) for p in points[:limit]],
            "next_offset": offset + limit if len(points) > limit else None, "gap_seconds": 30}


@router.websocket("/ws/locations")
async def locations(ws: WebSocket):
    await ws.accept()
    try:
        # Authenticate in the first frame, keeping credentials out of URLs/access logs.
        auth = await asyncio.wait_for(ws.receive_json(), timeout=5)
        token, org = auth.get("token", ""), auth.get("organization_id", "")
        if not isinstance(token, str) or not isinstance(org, str):
            raise ValueError("Invalid authentication")
        while True:
            with SessionLocal() as db:
                user_scope(token, org, db)  # Recheck revocation/membership on every snapshot.
                snapshot = latest_snapshot(db, org)
            await ws.send_json(snapshot)
            await asyncio.sleep(2)
    except (HTTPException, ValueError, AttributeError, asyncio.TimeoutError):
        await ws.close(code=1008)
    except WebSocketDisconnect:
        pass
