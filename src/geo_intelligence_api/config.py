from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Geo Intelligence API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://geo:geo@localhost:5432/geo"
    api_key: str
    log_level: str = "INFO"
    max_body_bytes: int = Field(default=1_048_576, gt=0)
    requests_per_minute: int = Field(default=120, gt=0)

    @model_validator(mode="after")
    def validate_api_key(self) -> "Settings":
        if self.api_key == "change-me" or len(self.api_key) < 32:
            raise ValueError("API_KEY segura com 32+ caracteres é obrigatória")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
