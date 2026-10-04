from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./music.db"
    jwt_secret: str = Field(min_length=32)
    jwt_issuer: str = "music-api"
    jwt_audience: str = "music-api-clients"
    access_token_minutes: int = Field(default=15, ge=1, le=60)


settings = Settings()
