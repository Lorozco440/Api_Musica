from fastapi import APIRouter, Response
from sqlalchemy import func, select
from .. import schemas as s
from ..models import Playlist, PlaylistSong, Song
from ..security import Db, CurrentUser
from ..services import owned_playlist, get_or_404, save, commit
from .catalog import Limit, Offset

router = APIRouter(prefix="/playlists", tags=["Playlists privadas"])


@router.post("", response_model=s.PlaylistOut, status_code=201)
def create(data: s.PlaylistIn, db: Db, user: CurrentUser):
    return save(db, Playlist(name=data.name, user_id=user.id))


@router.get("", response_model=list[s.PlaylistOut])
def list_own(db: Db, user: CurrentUser, limit: Limit = 20, offset: Offset = 0):
    return db.scalars(select(Playlist).where(Playlist.user_id == user.id)
                      .order_by(Playlist.id).limit(limit).offset(offset)).all()


@router.get("/{playlist_id}", response_model=s.PlaylistOut)
def detail(playlist_id: int, db: Db, user: CurrentUser):
    return owned_playlist(db, playlist_id, user.id)


@router.patch("/{playlist_id}", response_model=s.PlaylistOut)
def rename(playlist_id: int, data: s.PlaylistIn, db: Db, user: CurrentUser):
    playlist = owned_playlist(db, playlist_id, user.id)
    playlist.name = data.name
    return save(db, playlist)


@router.delete("/{playlist_id}", status_code=204)
def delete(playlist_id: int, db: Db, user: CurrentUser):
    db.delete(owned_playlist(db, playlist_id, user.id))
    commit(db)
    return Response(status_code=204)


@router.get("/{playlist_id}/songs", response_model=list[s.PlaylistEntry])
def songs(playlist_id: int, db: Db, user: CurrentUser, limit: Limit = 20, offset: Offset = 0):
    owned_playlist(db, playlist_id, user.id)
    rows = db.execute(select(Song, PlaylistSong.position).join(PlaylistSong, Song.id == PlaylistSong.song_id)
                      .where(PlaylistSong.playlist_id == playlist_id).order_by(PlaylistSong.position)
                      .limit(limit).offset(offset)).all()
    return [s.PlaylistEntry(**s.SongOut.model_validate(song).model_dump(), position=position)
            for song, position in rows]


@router.post("/{playlist_id}/songs", response_model=s.PlaylistEntry, status_code=201)
def add_song(playlist_id: int, data: s.AddSong, db: Db, user: CurrentUser):
    owned_playlist(db, playlist_id, user.id)
    song = get_or_404(db, Song, data.song_id)
    position = (db.scalar(select(func.max(PlaylistSong.position))
                          .where(PlaylistSong.playlist_id == playlist_id)) or 0) + 1
    save(db, PlaylistSong(playlist_id=playlist_id, song_id=song.id, position=position))
    return s.PlaylistEntry(**s.SongOut.model_validate(song).model_dump(), position=position)


@router.delete("/{playlist_id}/songs/{song_id}", status_code=204)
def remove_song(playlist_id: int, song_id: int, db: Db, user: CurrentUser):
    owned_playlist(db, playlist_id, user.id)
    db.delete(get_or_404(db, PlaylistSong, (playlist_id, song_id)))
    commit(db)
    return Response(status_code=204)
