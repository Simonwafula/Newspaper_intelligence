import os
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dev.db"

    # Storage
    storage_path: str = "./storage"

    # Processing limits
    max_pdf_size: str = "50MB"
    min_chars_for_native_text: int = 200
    processing_max_workers: int = 1
    processing_db_commit_interval: int = 5
    ocr_enabled: bool = True
    ocr_languages: str = "eng"

    # Development
    debug: bool = False
    log_level: str = "INFO"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Security - Legacy admin token (still supported)
    admin_token: str | None = None

    # JWT Authentication
    secret_key: str = secrets.token_urlsafe(32)  # Generate random key if not set
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure storage directory exists
os.makedirs(settings.storage_path, exist_ok=True)
os.makedirs(os.path.join(settings.storage_path, "editions"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_path, "pages"), exist_ok=True)
