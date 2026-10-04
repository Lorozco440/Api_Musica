from typing import Annotated
from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from .. import schemas as s
from ..models import Artist, Album, Song
from ..security import Db, CurrentUser, Admin
from ..services import get_or_404, save, commit

router = APIRouter(tags=["Catálogo"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/artists", response_model=list[s.ArtistOut])
def artists(db: Db, user: CurrentUser, limit: Limit = 20, offset: Offset = 0):
    return db.scalars(select(Artist).order_by(Artist.id).limit(limit).offset(offset)).all()


@router.post("/artists", response_model=s.ArtistOut, status_code=201)
def create_artist(data: s.ArtistIn, db: Db, admin: Admin):
    return save(db, Artist(**data.model_dump()))


@router.patch("/artists/{item_id}", response_model=s.ArtistOut)
def update_artist(item_id: int, data: s.ArtistIn, db: Db, admin: Admin):
    item = get_or_404(db, Artist, item_id)
    item.name = data.name
    return save(db, item)


@router.delete("/artists/{item_id}", status_code=204)
def delete_artist(item_id: int, db: Db, admin: Admin):
    db.delete(get_or_404(db, Artist, item_id))
    commit(db)
    return Response(status_code=204)


@router.get("/albums", response_model=list[s.AlbumOut])
def albums(db: Db, user: CurrentUser, limit: Limit = 20, offset: Offset = 0):
    return db.scalars(select(Album).order_by(Album.id).limit(limit).offset(offset)).all()


@router.post("/albums", response_model=s.AlbumOut, status_code=201)
def create_album(data: s.AlbumIn, db: Db, admin: Admin):
    get_or_404(db, Artist, data.artist_id)
    return save(db, Album(**data.model_dump()))


@router.put("/albums/{item_id}", response_model=s.AlbumOut)
def update_album(item_id: int, data: s.AlbumIn, db: Db, admin: Admin):
    item = get_or_404(db, Album, item_id)
    get_or_404(db, Artist, data.artist_id)
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    return save(db, item)


@router.delete("/albums/{item_id}", status_code=204)
def delete_album(item_id: int, db: Db, admin: Admin):
    db.delete(get_or_404(db, Album, item_id))
    commit(db)
    return Response(status_code=204)


@router.get("/songs", response_model=list[s.SongOut])
def songs(db: Db, user: CurrentUser, limit: Limit = 20, offset: Offset = 0,
          q: Annotated[str | None, Query(max_length=100)] = None):
    statement = select(Song)
    if q:
        statement = statement.where(Song.title.contains(q, autoescape=True))
    return db.scalars(statement.order_by(Song.id).limit(limit).offset(offset)).all()


@router.get("/songs/{item_id}", response_model=s.SongOut)
def song(item_id: int, db: Db, user: CurrentUser):
    return get_or_404(db, Song, item_id)


@router.post("/songs", response_model=s.SongOut, status_code=201)
def create_song(data: s.SongIn, db: Db, admin: Admin):
    get_or_404(db, Album, data.album_id)
    return save(db, Song(**data.model_dump()))


@router.patch("/songs/{item_id}", response_model=s.SongOut)
def update_song(item_id: int, data: s.SongPatch, db: Db, admin: Admin):
    item = get_or_404(db, Song, item_id)
    if data.album_id is not None:
        get_or_404(db, Album, data.album_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    return save(db, item)


@router.delete("/songs/{item_id}", status_code=204)
def delete_song(item_id: int, db: Db, admin: Admin):
    db.delete(get_or_404(db, Song, item_id))
    commit(db)
    return Response(status_code=204)
