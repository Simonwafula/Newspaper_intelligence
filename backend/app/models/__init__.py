from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
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
    EDITOR = "EDITOR"  # Can edit/categorize stories
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    alert_events = relationship("AlertEvent", cascade="all, delete-orphan")


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


# ==================== Intelligence Upgrade Models ====================

class Entity(Base):
    """Normalized entity storage for named entity recognition."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    name_normalized = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    entity_type = Column(String(20), nullable=False, index=True)  # PERSON, ORG, GPE, MONEY, DATE
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item_mentions = relationship("ItemEntity", back_populates="entity", cascade="all, delete-orphan")


class ItemEntity(Base):
    """Junction table linking items to entities with mention details."""
    __tablename__ = "item_entities"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    mention_count = Column(Integer, nullable=False, default=1)
    context_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item")
    entity = relationship("Entity", back_populates="item_mentions")


class TopicCluster(Base):
    """Topic clusters from semantic clustering of stories."""
    __tablename__ = "topic_clusters"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    centroid_vector = Column(JSON, nullable=True)  # Cluster centroid embedding
    cluster_size = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime(timezone=True), nullable=True)
    window_end = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    items = relationship("ItemTopic", back_populates="topic_cluster", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="topic_cluster")


class ItemTopic(Base):
    """Junction table linking items to topic clusters."""
    __tablename__ = "item_topics"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_cluster_id = Column(Integer, ForeignKey("topic_clusters.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item")
    topic_cluster = relationship("TopicCluster", back_populates="items")


class TrendMetric(Base):
    """Trend metrics for tracking topics and entities over time."""
    __tablename__ = "trend_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(DateTime, nullable=False, index=True)
    metric_name = Column(String(50), nullable=False, index=True)  # e.g., 'rising_topics', 'new_entities'
    key = Column(String(255), nullable=False, index=True)  # e.g., topic_id, entity_id
    value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Thread(Base):
    """Thread for connecting related stories across editions."""
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    key_entities_json = Column(JSON, nullable=True)  # Top entities in this thread
    topic_cluster_id = Column(Integer, ForeignKey("topic_clusters.id"), nullable=True)
    item_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    topic_cluster = relationship("TopicCluster", back_populates="threads")
    items = relationship("ThreadItem", back_populates="thread", cascade="all, delete-orphan")


class ThreadItem(Base):
    """Junction table linking threads to items with ordering."""
    __tablename__ = "thread_items"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=True)  # Relevance score for this item in thread

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("Thread", back_populates="items")
    item = relationship("Item")


class AlertEvent(Base):
    """Alert events for triggered alert rules."""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey("saved_searches.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    triggered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payload_json = Column(JSON, nullable=True)  # Alert details
    delivered = Column(Boolean, nullable=False, default=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
