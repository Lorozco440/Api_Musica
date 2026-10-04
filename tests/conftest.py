import os
os.environ['JWT_SECRET'] = 'test-key-only-not-for-deployment-1234567890'
os.environ['DATABASE_URL'] = 'sqlite://'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.rate_limit import limiter
from app.security import password_hasher, create_token


@pytest.fixture
def context(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "test.db"}', connect_args={'check_same_thread': False})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    limiter.entries.clear()
    with factory() as db:
        for name, role in [('admin', 'admin'), ('alice', 'client'), ('bob', 'client')]:
            db.add(User(name=name, email=f'{name}@example.com', role=role,
                        password_hash=password_hasher.hash('Valid-password-123')))
        db.commit()
    headers = {name: {'Authorization': f'Bearer {create_token(i)}'}
               for i, name in enumerate(['admin', 'alice', 'bob'], start=1)}
    with TestClient(app) as client:
        yield client, headers, factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def catalog(context):
    c, h, _ = context
    artist = c.post('/api/v1/artists', headers=h['admin'], json={'name': 'Artista'}).json()
    album = c.post('/api/v1/albums', headers=h['admin'], json={'title': 'Álbum', 'artist_id': artist['id']}).json()
    song = c.post('/api/v1/songs', headers=h['admin'], json={'title': 'Canción', 'album_id': album['id'], 'duration_seconds': 200}).json()
    return artist, album, song
