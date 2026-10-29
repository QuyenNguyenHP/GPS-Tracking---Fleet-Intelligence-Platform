from datetime import timedelta
import json
from sqlalchemy import func, select

from app.db import SessionLocal, utcnow
from app.models import Device, Position
from test_accounts import login, headers
from test_platform import send, telemetry


def params(**extra):
    return {'from': (utcnow()-timedelta(hours=1)).isoformat(), 'to': utcnow().isoformat(), **extra}


def test_database_explorer_auth_filters_pagination_and_raw_data(client):
    api, credentials = client
    a, b = credentials['organizations']
    admin, viewer = login(api, a), login(api, b)
    for org in [a, b]:
        assert send(api, org, {'samples': [telemetry(org, 1, 20), telemetry(org, 2, 10, False)]}, True).status_code == 200
    assert api.get('/api/v1/admin/devices', headers=headers(viewer)).status_code == 403
    assert api.get('/api/v1/admin/telemetry', headers=headers(viewer), params=params()).status_code == 403
    assert api.get('/api/v1/admin/telemetry', params=params()).status_code == 401
    inventory = api.get('/api/v1/admin/devices', headers=headers(admin), params={'organization_id':'demo'}).json()
    assert len(inventory['devices']) == 2
    assert inventory['database'] == 'SQLite'
    assert all('token_hash' not in row and row['organization_id']=='demo' for row in inventory['devices'])
    response = api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params(limit=1, organization_id='demo'))
    assert response.status_code == 200, response.text
    page = response.json()
    assert page['total'] == 2 and page['next_offset'] == 1
    assert page['records'][0]['fix_valid'] is False
    assert page['records'][0]['payload']['device_id'] == a['devices'][0]['device_id']
    assert page['records'][0]['latency_seconds'] >= 0
    page2 = api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params(limit=1, offset=1, organization_id='demo')).json()
    assert page2['next_offset'] is None and page2['records'][0]['sequence_number'] == 1
    all_orgs = api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params()).json()
    assert all_orgs['total'] == 4
    filtered = api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params(device_id=b['devices'][0]['device_id'], fix='invalid', sequence_number=2)).json()
    assert filtered['total'] == 1 and filtered['records'][0]['organization_id'] == 'other'
    mismatch = api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params(organization_id='demo', device_id=b['devices'][0]['device_id'])).json()
    assert mismatch['total'] == 0


def test_explorer_bounds_and_disabled_history(client):
    api, credentials = client
    a = credentials['organizations'][0]
    admin = login(api, a)
    send(api, a, telemetry(a, 1))
    with SessionLocal() as db:
        db.get(Device, a['devices'][0]['device_id']).enabled = False
        db.commit()
    assert len(api.get('/api/v1/devices/latest', headers=headers(admin)).json()['devices']) == 1
    assert api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params()).json()['total'] == 1
    for changes in [{'limit':201}, {'offset':-1}, {'fix':'unknown'}, {'from':(utcnow()-timedelta(days=8)).isoformat()}, {'from':'2026-10-28T00:00:00'}]:
        assert api.get('/api/v1/admin/telemetry', headers=headers(admin), params=params(**changes)).status_code == 422


def test_resize_twenty_preserves_history_credentials_and_disabled_devices(client, tmp_path):
    from seed_demo_company import seed
    api, credentials = client
    a = credentials['organizations'][0]
    send(api, a, telemetry(a, 1))
    with SessionLocal() as db:
        db.add(Device(id='demo-GPS-099', organization_id='demo', token_hash='retired-test-key'))
        db.commit()
    seed(20, tmp_path/'credentials.json', restrict_demo=True)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Device).where(Device.enabled.is_(True))) == 20
        assert not db.get(Device, 'demo-GPS-099').enabled
        assert db.scalar(select(func.count()).select_from(Position)) == 1
    updated = json.loads((tmp_path/'credentials.json').read_text())
    assert updated['organizations'][0]['devices'][0]['token'] == a['devices'][0]['token']
    assert len([d for d in updated['organizations'][0]['devices'] if d.get('enabled')]) == 20
