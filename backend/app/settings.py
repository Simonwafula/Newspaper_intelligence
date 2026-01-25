import os
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate backend root for env file path
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", os.path.join(_backend_root, ".env")),
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./dev.db"

    # Storage
    storage_path: str = "./storage"

    # Processing limits
    max_pdf_size: str = "50MB"
    min_chars_for_native_text: int = 200
    processing_max_workers: int = 1  # Default single-page processing
    processing_db_commit_interval: int = 5
    ocr_image_dpi: int = 250
    ocr_enabled: bool = True
    ocr_languages: str = "eng"
    tesseract_cmd: str | None = None
    archive_after_days: int = 5

    # Google Drive archiving
    gdrive_enabled: bool = False
    gdrive_folder_id: str | None = None
    gdrive_service_account_file: str | None = None

    # OneDrive archiving (personal accounts use refresh tokens)
    onedrive_enabled: bool = False
    onedrive_client_id: str | None = None
    onedrive_refresh_token: str | None = None
    onedrive_folder_path: str | None = None
    onedrive_token_file: str | None = None

    # Logs
    processing_log_dir: str = "./storage/logs"

    # Development
    debug: bool = False
    log_level: str = "INFO"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # JWT Authentication
    secret_key: str = secrets.token_urlsafe(32)  # Generate random key if not set
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure storage directory exists
os.makedirs(settings.storage_path, exist_ok=True)
os.makedirs(os.path.join(settings.storage_path, "editions"), exist_ok=True)
os.makedirs(os.path.join(settings.storage_path, "pages"), exist_ok=True)
os.makedirs(settings.processing_log_dir, exist_ok=True)
