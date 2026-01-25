from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class UserRole(str, PyEnum):
    """User roles for access control."""
    READER = "READER"  # Can read full articles
    ADMIN = "ADMIN"    # Can upload, process, manage


class AccessRequestStatus(str, PyEnum):
    """Access request status values."""
    PENDING = "PENDING"    # Awaiting admin review
    APPROVED = "APPROVED"  # Approved and user created
    REJECTED = "REJECTED"  # Rejected by admin


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)

    # Role-based access
    role = Column(String(20), nullable=False, default=UserRole.READER.value, index=True)

    # Account status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)  # Email verification

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return str(self.role) == UserRole.ADMIN.value


class Edition(Base):
    __tablename__ = "editions"

    id = Column(Integer, primary_key=True, index=True)
    newspaper_name = Column(String(200), nullable=False, index=True)
    edition_date = Column(DateTime, nullable=False, index=True)
    file_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    file_path = Column(String(500), nullable=False)
    pdf_local_path = Column(String(500), nullable=True)
    storage_backend = Column(String(20), nullable=False, default="local", index=True)
    storage_key = Column(String(500), nullable=True)
    num_pages = Column(Integer, nullable=False, default=0)
    total_pages = Column(Integer, nullable=False, default=0)
    processed_pages = Column(Integer, nullable=False, default=0)  # Progress tracking
    current_stage = Column(String(20), nullable=False, default="QUEUED", index=True)

    # Processing status
    status = Column(String(20), nullable=False, default="UPLOADED", index=True)  # UPLOADED, PROCESSING, READY, FAILED, ARCHIVED
    last_error = Column(Text, nullable=True)
    archive_status = Column(String(20), nullable=False, default="SCHEDULED", index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    cover_image_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    pages = relationship("Page", back_populates="edition", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="edition", cascade="all, delete-orphan")
    extraction_runs = relationship("ExtractionRun", back_populates="edition", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    char_count = Column(Integer, nullable=False, default=0)
    ocr_used = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)

    # Files and content
    image_path = Column(String(500), nullable=True)  # OCR image if needed
    extracted_text = Column(Text, nullable=True)

    # Layout information
    bbox_json = Column(JSON, nullable=True)  # Bounding boxes for text blocks

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    edition = relationship("Edition", back_populates="pages")
    items = relationship("Item", back_populates="page")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True)
    page_number = Column(Integer, nullable=False, index=True)

    # Item classification
    item_type = Column(String(20), nullable=False, index=True)  # STORY, AD, CLASSIFIED
    subtype = Column(String(20), nullable=True, index=True)  # TENDER, JOB, AUCTION, NOTICE, PROPERTY, OTHER

    # Content
    title = Column(Text, nullable=True)
    text = Column(Text, nullable=True)

    # Layout information
    bbox_json = Column(JSON, nullable=True)

    # Extracted entities
    extracted_entities_json = Column(JSON, nullable=True)

    # Structured classifieds fields
    contact_info_json = Column(JSON, nullable=True)  # Phone, email, address
    price_info_json = Column(JSON, nullable=True)     # Price, currency, negotiable
    date_info_json = Column(JSON, nullable=True)      # Event dates, deadlines
    location_info_json = Column(JSON, nullable=True)   # Locations, addresses
    classification_details_json = Column(JSON, nullable=True)  # Additional structured data
    structured_data = Column(JSON, nullable=True)       # Enhanced structured data for jobs/tenders

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    edition = relationship("Edition", back_populates="items")
    page = relationship("Page", back_populates="items")
    categories = relationship("ItemCategory", back_populates="item", cascade="all, delete-orphan")
    favorited_by = relationship("Favorite", back_populates="item", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="item", cascade="all, delete-orphan")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False)

    # Run metadata
    version = Column(String(20), nullable=False, default="1.0")
    success = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="RUNNING", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Logs and output
    log_path = Column(String(500), nullable=True)
    stats_json = Column(JSON, nullable=True)  # Items extracted, pages processed, etc.

    # Relationships
    edition = relationship("Edition", back_populates="extraction_runs")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Search parameters
    query = Column(Text, nullable=False)  # Search query text
    item_types = Column(JSON, nullable=True)  # Array of item types to filter
    date_from = Column(DateTime, nullable=True)  # Date range filter
    date_to = Column(DateTime, nullable=True)

    # Matching and notification
    match_count = Column(Integer, nullable=False, default=0)  # Current match count
    last_run = Column(DateTime(timezone=True), nullable=True)  # When matches were last calculated
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccessRequest(Base):
    """Access request model for invite-based registration."""
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Requester information
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    organization = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)

    # Request details
    reason = Column(Text, nullable=False)  # Reason for access / intended use

    # Request status and processing
    status = Column(String(20), nullable=False, default=AccessRequestStatus.PENDING.value, index=True)
    processed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(Text, nullable=True)  # Admin notes on approval/rejection

    # Anti-spam and tracking
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    honeypot_field = Column(String(100), nullable=True)  # Bot detection

    # Consent
    consent_not_redistribute = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    processed_by = relationship("User", foreign_keys=[processed_by_user_id])


class UserAPIKey(Base):
    """API keys for external application access."""
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # User-friendly name for the key
    key_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash
    key_prefix = Column(String(10), nullable=False)  # First few characters for identification
    description = Column(Text, nullable=True)  # Key purpose/description

    # Permissions and limits
    permissions = Column(JSON, nullable=True)  # Array of allowed endpoints/resources
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)  # Requests per hour
    rate_limit_per_day = Column(Integer, nullable=False, default=10000)  # Requests per day

    # Status and tracking
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(Integer, nullable=False, default=0)  # Total requests ever made

    # Validity period
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration

    # Metadata
    created_from_ip = Column(String(45), nullable=True)  # IP address that created the key
    user_agent = Column(Text, nullable=True)  # Browser/client info

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")


class Favorite(Base):
    """User-specific bookmarks for newspaper items."""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)

    # Metadata
    notes = Column(Text, nullable=True)  # Personal notes on this favorite
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorites")
    item = relationship("Item", back_populates="favorited_by")


class Collection(Base):
    """User-managed groups of items for research or personal interest."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=False, default="#3B82F6")  # Hex color for UI

    # Settings
    is_public = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="collections")
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    """Junction table for collections and items with per-item notes."""
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)

    # Research metadata
    notes = Column(Text, nullable=True)  # Research notes or annotations
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="items")
    item = relationship("Item", back_populates="collection_items")


class Category(Base):
    """Topic categories for organizing and classifying newspaper items."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # "Economics", "Politics", "Labor", etc.
    slug = Column(String(100), nullable=False, unique=True, index=True)  # URL-friendly version
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=False, default="#6B7280")  # Hex color for UI badges
    keywords = Column(JSON, nullable=True)  # List of keywords for auto-classification
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Ordering
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    item_categories = relationship("ItemCategory", back_populates="category", cascade="all, delete-orphan")


class ItemCategory(Base):
    """Junction table linking items to categories."""
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Classification metadata
    confidence = Column(Integer, nullable=False, default=50)  # 0-100 confidence score
    source = Column(String(20), nullable=False, default="auto")  # "auto" or "manual"
    notes = Column(Text, nullable=True)  # Optional notes on classification reasoning

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    item = relationship("Item", back_populates="categories")
    category = relationship("Category", back_populates="item_categories")

    # Ensure each item-category combination is unique
    __table_args__ = (
        UniqueConstraint('item_id', 'category_id', name='_item_category_uc'),
        {"sqlite_autoincrement": True}
    )


class WebhookEventType(str, PyEnum):
    """Types of events that can trigger webhooks."""
    EDITION_CREATED = "edition.created"
    EDITION_PROCESSED = "edition.processed"
    EDITION_FAILED = "edition.failed"
    ITEMS_EXTRACTED = "items.extracted"
    NEW_JOBS = "items.new_jobs"
    NEW_TENDERS = "items.new_tenders"


class Webhook(Base):
    """Webhook subscriptions for external notifications."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)  # Webhook endpoint URL
    secret = Column(String(64), nullable=True)  # Optional secret for HMAC signing

    # Event subscriptions
    events = Column(JSON, nullable=False)  # List of WebhookEventType values

    # Status and settings
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    retry_count = Column(Integer, nullable=False, default=3)  # Max retries on failure
    timeout_seconds = Column(Integer, nullable=False, default=30)

    # Health tracking
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    total_deliveries = Column(Integer, nullable=False, default=0)
    successful_deliveries = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Log of webhook delivery attempts."""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False, index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)  # The data sent to the webhook

    # Delivery status
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, success, failed
    attempts = Column(Integer, nullable=False, default=0)
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
