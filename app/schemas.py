from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=150)]
PositiveId = Annotated[int, Field(gt=0)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    # Do not strip passwords: spaces are legitimate password characters.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío")
        return value.strip()


class Login(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class ProfileUpdate(Input):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ArtistIn(Input):
    name: Name


class ArtistOut(ArtistIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AlbumIn(Input):
    title: Name
    artist_id: PositiveId


class AlbumOut(AlbumIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SongIn(Input):
    title: Name
    album_id: PositiveId
    duration_seconds: Annotated[int, Field(gt=0, le=86400)]


class SongOut(SongIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SongPatch(Input):
    title: Name | None = None
    album_id: PositiveId | None = None
    duration_seconds: Annotated[int, Field(gt=0, le=86400)] | None = None

    @model_validator(mode="after")
    def reject_empty_and_null(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Envíe al menos un campo y no utilice null")
        return self


class PlaylistIn(Input):
    name: Name


class PlaylistOut(PlaylistIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


class PlaylistEntry(SongOut):
    position: int


class AddSong(Input):
    song_id: PositiveId
