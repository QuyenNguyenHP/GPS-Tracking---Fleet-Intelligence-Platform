from datetime import timedelta

from sqlalchemy import select

from app.auth import digest
from app.auth.passwords import verify_password
from app.db import SessionLocal, utcnow
from app.models import LoginSession, User


def login(api, org):
    result = api.post('/api/v1/auth/login', json=org['account'])
    assert result.status_code == 200, result.text
    return result.json()


def headers(session, org='demo'):
    return {'Authorization': 'Bearer ' + session['token'], 'X-Organization-ID': org}


def new_user(**overrides):
    return {'username': 'dispatcher', 'name': 'Dispatcher', 'password': 'a-long-test-password',
            'organization_ids': ['demo'], 'enabled': True, 'is_platform_admin': False, **overrides}


def test_account_login_sessions_and_logout(client):
    api, credentials = client
    org = credentials['organizations'][0]
    session = login(api, org)
    assert session['user']['is_platform_admin'] is True
    assert [o['id'] for o in session['user']['organizations']] == ['demo']
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == 'admin'))
        assert user.password_hash != org['account']['password']
        assert verify_password(org['account']['password'], user.password_hash)
        assert db.get(LoginSession, digest(session['token']))
    assert api.get('/api/v1/auth/me', headers=headers(session)).status_code == 200
    with api.websocket_connect('/api/v1/ws/locations') as ws:
        ws.send_json({'token': session['token'], 'organization_id': 'demo'})
        assert len(ws.receive_json()['devices']) == 2
    assert api.get('/api/v1/assets', headers=headers(session, 'other')).status_code == 403
    assert api.post('/api/v1/auth/logout', headers=headers(session)).status_code == 200
    assert api.get('/api/v1/auth/me', headers=headers(session)).status_code == 401
    with api.websocket_connect('/api/v1/ws/locations') as ws:
        ws.send_json({'token': session['token'], 'organization_id': 'demo'})
        assert ws.receive()['code'] == 1008


def test_bad_login_rate_limit_and_expiration(client):
    api, credentials = client
    assert api.post('/api/v1/auth/login', json={'username': 'missing', 'password': 'wrong'}).status_code == 401
    session = login(api, credentials['organizations'][0])
    with SessionLocal() as db:
        db.get(LoginSession, digest(session['token'])).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert api.get('/api/v1/admin/users', headers=headers(session)).status_code == 401
    for _ in range(8):
        assert api.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'wrong'}).status_code == 401
    limited = api.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'wrong'})
    assert limited.status_code == 429
    assert limited.headers['retry-after'] == '60'


def test_viewer_device_and_legacy_tokens_cannot_admin(client):
    api, credentials = client
    a, b = credentials['organizations']
    viewer = login(api, b)
    for path in ['/api/v1/admin/users', '/api/v1/admin/organizations']:
        assert api.get(path, headers=headers(viewer)).status_code == 403
        assert api.get(path, headers={'Authorization': 'Bearer ' + a['operator_token']}).status_code == 401
        assert api.get(path, headers={'Authorization': 'Bearer ' + a['devices'][0]['token']}).status_code == 401
        assert api.post(path, headers=headers(viewer), json={}).status_code == 403
    assert api.put('/api/v1/admin/users/demo-account', headers=headers(viewer), json=new_user()).status_code == 403


def test_admin_create_organization_account_memberships_and_duplicates(client):
    api, credentials = client
    admin = login(api, credentials['organizations'][0])
    h = headers(admin)
    assert api.post('/api/v1/admin/organizations', headers=h, json={'id': 'new-company', 'name': 'New Company'}).status_code == 201
    assert api.post('/api/v1/admin/organizations', headers=h, json={'id': 'new-company', 'name': 'Duplicate'}).status_code == 409
    created = api.post('/api/v1/admin/users', headers=h, json=new_user(organization_ids=['new-company']))
    assert created.status_code == 201
    assert 'password' not in created.json() and 'token_hash' not in created.json()
    assert api.post('/api/v1/admin/users', headers=h, json=new_user(username='DISPATCHER')).status_code == 409
    assert api.post('/api/v1/admin/users', headers=h, json=new_user(username='bad', organization_ids=['missing'])).status_code == 422
    user_session = api.post('/api/v1/auth/login', json={'username': 'DISPATCHER', 'password': 'a-long-test-password'}).json()
    assert api.get('/api/v1/assets', headers=headers(user_session, 'new-company')).status_code == 200
    assert api.get('/api/v1/assets', headers=headers(user_session, 'demo')).status_code == 403
    body = new_user(organization_ids=['demo', 'other'])
    del body['username'], body['password']
    assert api.put('/api/v1/admin/users/' + created.json()['id'], headers=h, json=body).status_code == 200
    assert api.get('/api/v1/assets', headers=headers(user_session, 'new-company')).status_code == 403
    assert api.get('/api/v1/assets', headers=headers(user_session, 'other')).status_code == 200


def test_reset_disable_and_self_protection(client):
    api, credentials = client
    a, b = credentials['organizations']
    admin, viewer = login(api, a), login(api, b)
    body = {'name': 'Harbor Viewer', 'organization_ids': ['other'], 'enabled': True,
            'is_platform_admin': False, 'password': 'replacement-test-password'}
    assert api.put('/api/v1/admin/users/other-account', headers=headers(admin), json=body).status_code == 200
    assert api.get('/api/v1/auth/me', headers=headers(viewer)).status_code == 401
    assert api.post('/api/v1/auth/login', json=b['account']).status_code == 401
    viewer = api.post('/api/v1/auth/login', json={'username': 'other.viewer', 'password': body['password']}).json()
    del body['password']
    body['enabled'] = False
    assert api.put('/api/v1/admin/users/other-account', headers=headers(admin), json=body).status_code == 200
    assert api.get('/api/v1/auth/me', headers=headers(viewer)).status_code == 401
    assert api.post('/api/v1/auth/login', json={'username': 'other.viewer', 'password': 'replacement-test-password'}).status_code == 401
    assert api.put('/api/v1/admin/users/demo-account', headers=headers(admin), json={**body, 'is_platform_admin': True}).status_code == 409
    assert api.put('/api/v1/admin/users/demo-account', headers=headers(admin), json={**body, 'enabled': True}).status_code == 409


def test_disabled_organization_blocks_rest_websocket_and_ingestion(client):
    api, credentials = client
    a, b = credentials['organizations']
    admin, viewer = login(api, a), login(api, b)
    assert api.put('/api/v1/admin/organizations/other', headers=headers(admin), json={'name': 'Paused company', 'enabled': False}).status_code == 200
    assert api.get('/api/v1/assets', headers=headers(viewer, 'other')).status_code == 403
    assert api.get('/api/v1/auth/me', headers=headers(viewer)).json()['organizations'] == []
    with api.websocket_connect('/api/v1/ws/locations') as ws:
        ws.send_json({'token': viewer['token'], 'organization_id': 'other'})
        assert ws.receive()['code'] == 1008
    payload = {'schema_version': 1, 'device_id': b['devices'][0]['device_id'], 'sequence_number': 1,
               'recorded_at': utcnow().isoformat(), 'location': {'fix_valid': False}}
    assert api.post('/api/v1/telemetry', json=payload, headers={'Authorization': 'Bearer ' + b['devices'][0]['token']}).status_code == 401
    assert api.put('/api/v1/admin/organizations/other', headers=headers(admin), json={'name': 'Restored company', 'enabled': True}).status_code == 200
    assert api.get('/api/v1/assets', headers=headers(viewer, 'other')).status_code == 200


def test_seed_does_not_reset_account_changes(client, tmp_path):
    from app.auth.passwords import hash_password
    from seed_demo_company import seed
    api, credentials = client
    with SessionLocal() as db:
        user = db.get(User, 'demo-account')
        user.password_hash = hash_password('changed-admin-password')
        user.enabled = False
        db.commit()
    seed(2, tmp_path / 'credentials.json')
    with SessionLocal() as db:
        user = db.get(User, 'demo-account')
        assert not user.enabled
        assert verify_password('changed-admin-password', user.password_hash)
    assert api.post('/api/v1/auth/login', json=credentials['organizations'][0]['account']).status_code == 401


def test_local_password_recovery_revokes_sessions_without_changing_role(client):
    from reset_account_password import reset_password
    api, credentials = client
    org = credentials['organizations'][0]
    session = login(api, org)
    reset_password('admin', 'recovered-admin-password')
    assert api.get('/api/v1/auth/me', headers=headers(session)).status_code == 401
    assert api.post('/api/v1/auth/login', json=org['account']).status_code == 401
    result = api.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'recovered-admin-password'})
    assert result.status_code == 200
    assert result.json()['user']['is_platform_admin'] is True


def test_eight_character_password_policy_and_default_admin(client):
    import pytest
    from pydantic import ValidationError
    from app.api.admin import UserCreate, UserUpdate
    from reset_account_password import reset_password
    api, credentials = client
    assert credentials['organizations'][0]['account']['password'] == 'admin123'
    assert login(api, credentials['organizations'][0])['user']['is_platform_admin']
    UserCreate(**new_user(password='admin123'))
    UserUpdate(name='Admin', organization_ids=['demo'], password='admin123')
    with pytest.raises(ValidationError):
        UserCreate(**new_user(password='short12'))
    with pytest.raises(ValidationError):
        UserUpdate(name='Admin', organization_ids=['demo'], password='short12')
    with pytest.raises(ValueError):
        reset_password('admin', 'short12')
    reset_password('admin', 'admin123')
    assert login(api, credentials['organizations'][0])['user']['is_platform_admin']
