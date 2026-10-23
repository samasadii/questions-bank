from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "سامانه بانک سؤال"
    database_url: str = "sqlite:///./questions_bank.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    frontend_origin: str = "http://localhost:5173"
    upload_dir: Path = Path("./uploads")
    max_image_bytes: int = 5 * 1024 * 1024
    max_image_pixels: int = 20_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

