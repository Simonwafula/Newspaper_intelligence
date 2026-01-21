from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dev.db"
    
    # Storage
    storage_path: str = "./storage"
    
    # Processing limits
    max_pdf_size: str = "50MB"
    min_chars_for_native_text: int = 200
    ocr_enabled: bool = True
    ocr_languages: str = "eng"
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
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