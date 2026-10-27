from datetime import timedelta
import pytest
from app.db import SessionLocal, utcnow, utc
from app.models import Device, Position, Assignment, Asset
from sqlalchemy import select, func


def headers(org):
    return {"Authorization": "Bearer " + org["operator_token"], "X-Organization-ID": org["id"]}


def telemetry(org, seq=1, age=0, fix=True):
    return {"schema_version": 1, "device_id": org["devices"][0]["device_id"], "sequence_number": seq,
            "recorded_at": (utcnow() - timedelta(seconds=age)).isoformat(),
            "location": {"fix_valid": fix, **({"latitude": 1.3, "longitude": 103.8} if fix else {})}}


def send(client, org, payload, batch=False):
    return client.post("/api/v1/telemetry" + ("/batch" if batch else ""), json=payload,
                       headers={"Authorization": "Bearer " + org["devices"][0]["token"]})


def test_duplicates_late_replay_heartbeat_and_order(client):
    api, credentials = client
    org = credentials["organizations"][0]
    newest, older, heartbeat = telemetry(org, 1, 10), telemetry(org, 2, 60), telemetry(org, 3, 0, False)
    ack = send(api, org, {"samples": [newest, older, newest, heartbeat]}, True)
    assert ack.status_code == 200
    assert ack.json() == {"accepted": [1, 2, 3], "duplicates": [1]}
    current = api.get("/api/v1/devices/latest", headers=headers(org)).json()["devices"][0]
    assert current["position"]["sequence_number"] == 1
    assert current["state"] == "live"
    history = api.get(f"/api/v1/assets/{org['devices'][0]['asset_id']}/positions", headers=headers(org),
        params={"from": (utcnow() - timedelta(minutes=5)).isoformat(), "to": utcnow().isoformat()}).json()
    assert [p["sequence_number"] for p in history["points"]] == [2, 1, 3]
    assert history["points"][-1]["fix_valid"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Position)) == 3


def test_tenant_isolation_and_device_impersonation(client):
    api, credentials = client
    a, b = credentials["organizations"]
    assert api.get("/api/v1/assets").status_code == 401
    assert api.get("/api/v1/assets", headers={**headers(a), "X-Organization-ID": b["id"]}).status_code == 403
    assert all(item["id"].startswith("demo-") for item in api.get("/api/v1/assets", headers=headers(a)).json())
    query = {"from": (utcnow() - timedelta(hours=1)).isoformat(), "to": utcnow().isoformat()}
    assert api.get(f"/api/v1/assets/{b['devices'][0]['asset_id']}/positions", headers=headers(a), params=query).status_code == 404
    assert send(api, a, telemetry(b)).status_code == 403
    assert api.get("/api/v1/assets", headers={"Authorization": "Bearer " + a["devices"][0]["token"], "X-Organization-ID": a["id"]}).status_code == 401


def test_atomic_conflict_and_revocation(client):
    api, credentials = client
    org = credentials["organizations"][0]
    first = telemetry(org)
    assert send(api, org, first).status_code == 200
    changed = {**first, "location": {"fix_valid": True, "latitude": 2, "longitude": 104}}
    assert send(api, org, {"samples": [telemetry(org, 2), changed]}, True).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Position)) == 1
        db.get(Device, first["device_id"]).enabled = False
        db.commit()
    assert send(api, org, telemetry(org, 3)).status_code == 401


@pytest.mark.parametrize("change", [
    {"recorded_at": "2026-10-27T00:00:00"},
    {"recorded_at": "2099-01-01T00:00:00Z"},
    {"sequence_number": -1}, {"sequence_number": 1.5},
    {"location": {"fix_valid": True, "latitude": 91, "longitude": 103}},
    {"location": {"fix_valid": True}},
    {"location": {"fix_valid": False, "latitude": 1, "longitude": 103}},
])
def test_validation(client, change):
    api, credentials = client
    org = credentials["organizations"][0]
    assert send(api, org, {**telemetry(org), **change}).status_code == 422


def test_body_batch_and_history_bounds(client):
    api, credentials = client
    org = credentials["organizations"][0]
    assert send(api, org, {"samples": [telemetry(org)] * 201}, True).status_code == 422
    assert api.post("/api/v1/telemetry", content="x" * 262145).status_code == 413
    assert api.get(f"/api/v1/assets/{org['devices'][0]['asset_id']}/positions", headers=headers(org),
        params={"from": (utcnow() - timedelta(days=8)).isoformat(), "to": utcnow().isoformat()}).status_code == 422


def test_stale_and_offline_are_separate_from_last_position(client):
    api, credentials = client
    org = credentials["organizations"][0]
    send(api, org, telemetry(org, age=70))
    endpoint = "/api/v1/devices/latest"
    assert api.get(endpoint, headers=headers(org)).json()["devices"][0]["state"] == "stale"
    with SessionLocal() as db:
        db.get(Device, org["devices"][0]["device_id"]).last_seen_at = utcnow() - timedelta(seconds=130)
        db.commit()
    snapshot = api.get(endpoint, headers=headers(org)).json()["devices"][0]
    assert snapshot["state"] == "offline"
    assert snapshot["position"] is not None


def test_websocket_scope(client):
    api, credentials = client
    a, b = credentials["organizations"]
    with api.websocket_connect("/api/v1/ws/locations") as ws:
        ws.send_json({"token": a["operator_token"], "organization_id": a["id"]})
        snapshot = ws.receive_json()
        assert len(snapshot["devices"]) == 2
        assert all(d["device_id"].startswith("demo-") for d in snapshot["devices"])
    from starlette.websockets import WebSocketDisconnect
    with api.websocket_connect("/api/v1/ws/locations") as ws:
        ws.send_json({"token": a["operator_token"], "organization_id": b["id"]})
        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()
        assert error.value.code == 1008


def test_assignment_is_resolved_at_capture_time_and_pagination(client):
    api, credentials = client
    org = credentials["organizations"][0]
    boundary = utcnow() - timedelta(seconds=30)
    with SessionLocal() as db:
        assignment = db.scalar(select(Assignment).where(Assignment.device_id == org["devices"][0]["device_id"]))
        assignment.valid_to = boundary
        db.add(Assignment(device_id=assignment.device_id, asset_id=org["devices"][1]["asset_id"], valid_from=boundary))
        db.commit()
    assert send(api, org, {"samples": [telemetry(org, 1, 60), telemetry(org, 2, 50), telemetry(org, 3, 0)]}, True).status_code == 200
    url = f"/api/v1/assets/{org['devices'][0]['asset_id']}/positions"
    params = {"from": (utcnow() - timedelta(minutes=5)).isoformat(), "to": utcnow().isoformat(), "limit": 1}
    page1 = api.get(url, headers=headers(org), params=params).json()
    page2 = api.get(url, headers=headers(org), params={**params, "offset": page1["next_offset"]}).json()
    assert [page1["points"][0]["sequence_number"], page2["points"][0]["sequence_number"]] == [1, 2]
    assert page2["next_offset"] is None
