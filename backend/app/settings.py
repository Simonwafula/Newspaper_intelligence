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
    ocr_preprocess: bool = True
    ocr_preprocess_unsharp: bool = True
    ocr_preprocess_adaptive: bool = True
    ocr_preprocess_global_threshold: int = 170
    ocr_confidence_threshold: int = 55
    ocr_retry_enabled: bool = True
    ocr_retry_dpi: int = 350
    ocr_psm: int = 3
    ocr_retry_psm: int = 4
    ocr_fallback_enabled: bool = False
    ocr_fallback_lang: str = "en"
    tesseract_cmd: str | None = None

    # Story grouping
    story_grouping_enabled: bool = True
    story_grouping_page_window: int = 2
    story_grouping_similarity_threshold: float = 0.35
    story_grouping_min_shared_tokens: int = 3
    archive_after_days: int = 5

    # === ADVANCED LAYOUT DETECTION (Phase 1+) ===
    # Master feature flag - set to True to enable ML-based pipeline
    advanced_layout_enabled: bool = False

    # High-DPI page rendering
    layout_detection_dpi: int = 300  # 300-450 DPI recommended for layout detection
    layout_detection_width: int = 2500  # Alternative to DPI - target width in pixels
    layout_detection_method: str = "auto"  # auto, detectron2, layoutparser, heuristic

    # Layout detection model configuration
    layout_model_device: str = "cpu"  # cpu or cuda
    layout_model_path: str | None = None  # Custom model path if needed
    layout_model_name: str = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"
    layout_confidence_threshold: float = 0.7  # Min confidence for block detection

    # Block-level OCR settings
    block_ocr_enabled: bool = True
    block_ocr_engine: str = "paddle"  # paddle, tesseract, auto
    block_ocr_lang: str = "en"  # OCR language code
    block_ocr_confidence_threshold: float = 0.5  # Min confidence for word detection

    # Reading order detection
    reading_order_enabled: bool = True

    # === SEMANTIC STORY GROUPING (Phase 6+) ===
    semantic_grouping_enabled: bool = False  # Enable BGE embeddings for story grouping
    semantic_model_name: str = "BAAI/bge-small-en-v1.5"  # BGE model for embeddings
    semantic_model_device: str = "cpu"  # cpu or cuda
    semantic_similarity_threshold: float = 0.65  # Min similarity for story continuation
    semantic_embedding_dim: int = 384  # Embedding dimension (384 for bge-small)

    # Hybrid story grouping weights
    semantic_weight: float = 0.4  # Weight for semantic similarity
    token_weight: float = 0.3  # Weight for token overlap
    explicit_ref_weight: float = 0.3  # Weight for explicit page references

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
