from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Playlist


def get_or_404(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, "Recurso no encontrado")
    return item


def commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicto: registro duplicado o recurso con relaciones existentes") from None


def save(db: Session, item):
    db.add(item)
    commit(db)
    db.refresh(item)
    return item


def owned_playlist(db: Session, playlist_id: int, user_id: int):
    playlist = get_or_404(db, Playlist, playlist_id)
    # Use the same response as a missing resource to avoid exposing other users' data.
    if playlist.user_id != user_id:
        raise HTTPException(404, "Recurso no encontrado")
    return playlist
