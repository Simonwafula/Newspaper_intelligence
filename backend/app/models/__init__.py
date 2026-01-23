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
    num_pages = Column(Integer, nullable=False, default=0)

    # Processing status
    status = Column(String(20), nullable=False, default="UPLOADED", index=True)  # UPLOADED, PROCESSING, READY, FAILED
    error_message = Column(Text, nullable=True)

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


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False)

    # Run metadata
    version = Column(String(20), nullable=False, default="1.0")
    success = Column(Boolean, nullable=False, default=False)

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
    user = relationship("User", foreign_keys=[user_id])


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
        {"sqlite_autoincrement": True}
    )
