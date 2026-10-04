from datetime import datetime, timedelta, timezone
import jwt
import pytest
from sqlalchemy import select
from app.config import settings
from app.models import User, PlaylistSong
from app.security import password_hasher


def test_register_login_profile(context):
    c, h, factory = context
    payload = {'name': 'Carla', 'email': 'Carla@example.com', 'password': 'A-strong-password-123'}
    result = c.post('/api/v1/auth/register', json=payload)
    assert result.status_code == 201
    assert result.json()['role'] == 'client'
    assert 'password_hash' not in result.text and payload['password'] not in result.text
    with factory() as db:
        user = db.scalar(select(User).where(User.email == 'carla@example.com'))
        assert user.password_hash.startswith('$argon2id$')
        assert password_hasher.verify(payload['password'], user.password_hash)
    assert c.post('/api/v1/auth/register', json=payload).status_code == 409
    login = c.post('/api/v1/auth/login', json={'email': payload['email'], 'password': payload['password']})
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    assert c.get('/api/v1/users/me', headers=headers).json()['name'] == 'Carla'
    assert c.patch('/api/v1/users/me', headers=headers, json={'name': 'Carla Nueva'}).json()['name'] == 'Carla Nueva'


def test_privilege_escalation_and_bad_credentials(context):
    c, h, _ = context
    response = c.post('/api/v1/auth/register', json={'name': 'X', 'email': 'x@example.com', 'password': 'Valid-password-123', 'role': 'admin'})
    assert response.status_code == 422
    assert c.patch('/api/v1/users/me', headers=h['alice'], json={'name': 'Alice', 'role': 'admin'}).status_code == 422
    for email in ['alice@example.com', 'missing@example.com']:
        response = c.post('/api/v1/auth/login', json={'email': email, 'password': 'wrong'})
        assert response.status_code == 401
        assert response.json()['error']['message'] == 'Credenciales incorrectas'
    assert c.post('/api/v1/artists', headers=h['alice'], json={'name': 'No'}).status_code == 403


@pytest.mark.parametrize('case', ['missing', 'garbage', 'expired', 'signature', 'audience', 'issuer', 'no-exp', 'deleted-user', 'algorithm'])
def test_reject_invalid_tokens(context, case):
    c, _, _ = context
    now = datetime.now(timezone.utc)
    payload = {'sub': '2', 'iat': now, 'exp': now + timedelta(minutes=15), 'iss': settings.jwt_issuer, 'aud': settings.jwt_audience}
    secret = settings.jwt_secret
    algorithm = 'HS256'
    if case == 'expired': payload['exp'] = now - timedelta(seconds=1)
    if case == 'signature': secret = 'different-secret-key-at-least-32-characters'
    if case == 'audience': payload['aud'] = 'wrong'
    if case == 'issuer': payload['iss'] = 'wrong'
    if case == 'no-exp': del payload['exp']
    if case == 'deleted-user': payload['sub'] = '9999'
    if case == 'algorithm': algorithm = 'HS384'
    token = jwt.encode(payload, secret, algorithm=algorithm)
    headers = {} if case == 'missing' else {'Authorization': 'Bearer ' + ('bad-token' if case == 'garbage' else token)}
    response = c.get('/api/v1/users/me', headers=headers)
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'


def test_catalog_crud_and_integrity(context, catalog):
    c, h, _ = context
    artist, album, song = catalog
    assert c.get('/api/v1/songs?q=Canci&limit=1', headers=h['alice']).json()[0]['id'] == song['id']
    assert c.get('/api/v1/songs?limit=101', headers=h['alice']).status_code == 422
    assert c.get('/api/v1/songs?offset=1', headers=h['alice']).json() == []
    assert c.delete(f'/api/v1/artists/{artist["id"]}', headers=h['admin']).status_code == 409
    assert c.delete(f'/api/v1/albums/{album["id"]}', headers=h['admin']).status_code == 409
    assert c.patch(f'/api/v1/songs/{song["id"]}', headers=h['admin'], json={'title': 'Nuevo título'}).status_code == 200
    assert c.patch(f'/api/v1/songs/{song["id"]}', headers=h['admin'], json={'duration_seconds': -1}).status_code == 422
    assert c.patch(f'/api/v1/songs/{song["id"]}', headers=h['admin'], json={'title': None}).status_code == 422
    assert c.post('/api/v1/songs', headers=h['admin'], json={'title': 'X', 'album_id': 9999, 'duration_seconds': 2}).status_code == 404
    assert c.delete(f'/api/v1/songs/{song["id"]}', headers=h['admin']).status_code == 204
    assert c.get(f'/api/v1/songs/{song["id"]}', headers=h['alice']).status_code == 404
    assert c.delete(f'/api/v1/albums/{album["id"]}', headers=h['admin']).status_code == 204
    assert c.delete(f'/api/v1/artists/{artist["id"]}', headers=h['admin']).status_code == 204


def test_playlist_ownership_order_duplicates_and_cascade(context, catalog):
    c, h, factory = context
    _, album, song = catalog
    response = c.post('/api/v1/playlists', headers=h['alice'], json={'name': 'Favoritas'})
    assert response.status_code == 201
    pid = response.json()['id']
    path = f'/api/v1/playlists/{pid}'
    assert c.get('/api/v1/playlists', headers=h['bob']).json() == []
    for role in ['bob', 'admin']:
        assert c.get(path, headers=h[role]).status_code == 404
        assert c.patch(path, headers=h[role], json={'name': 'Hack'}).status_code == 404
        assert c.delete(path, headers=h[role]).status_code == 404
        assert c.post(path+'/songs', headers=h[role], json={'song_id': song['id']}).status_code == 404
        assert c.get(path+'/songs', headers=h[role]).status_code == 404
        assert c.delete(path+f'/songs/{song["id"]}', headers=h[role]).status_code == 404
    assert c.post(path+'/songs', headers=h['alice'], json={'song_id': song['id']}).json()['position'] == 1
    assert c.post(path+'/songs', headers=h['alice'], json={'song_id': song['id']}).status_code == 409
    assert c.post(path+'/songs', headers=h['alice'], json={'song_id': 9999}).status_code == 404
    second = c.post('/api/v1/songs', headers=h['admin'], json={'title': 'Segunda', 'album_id': album['id'], 'duration_seconds': 100}).json()
    assert c.post(path+'/songs', headers=h['alice'], json={'song_id': second['id']}).json()['position'] == 2
    assert [x['position'] for x in c.get(path+'/songs', headers=h['alice']).json()] == [1, 2]
    assert c.delete(path+f'/songs/{song["id"]}', headers=h['alice']).status_code == 204
    assert c.patch(path, headers=h['alice'], json={'name': 'Nueva'}).json()['name'] == 'Nueva'
    assert c.delete(path, headers=h['alice']).status_code == 204
    with factory() as db:
        assert db.scalar(select(PlaylistSong)) is None


def test_rate_limit_and_safe_validation(context):
    c, _, _ = context
    response = c.post('/api/v1/auth/register', json={'name': ' ', 'email': 'invalid', 'password': 'SECRET'})
    assert response.status_code == 422
    assert 'SECRET' not in response.text
    for _ in range(10):
        response = c.post('/api/v1/auth/login', json={'email': 'alice@example.com', 'password': 'wrong'})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '60'


def test_health_and_openapi(context):
    c, _, _ = context
    assert c.get('/health').json() == {'status': 'ok'}
    schema = c.get('/openapi.json').json()
    assert schema['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'
    assert '/api/v1/playlists/{playlist_id}/songs' in schema['paths']
