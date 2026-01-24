from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EditionStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class EditionStage(str, Enum):
    QUEUED = "QUEUED"
    EXTRACT = "EXTRACT"
    OCR = "OCR"
    LAYOUT = "LAYOUT"
    INDEX = "INDEX"
    DONE = "DONE"


class ArchiveStatus(str, Enum):
    NOT_SCHEDULED = "NOT_SCHEDULED"
    SCHEDULED = "SCHEDULED"
    ARCHIVING = "ARCHIVING"
    ARCHIVED = "ARCHIVED"
    ARCHIVE_FAILED = "ARCHIVE_FAILED"


class PageStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class ExtractionRunStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ItemType(str, Enum):
    STORY = "STORY"
    AD = "AD"
    CLASSIFIED = "CLASSIFIED"


class ItemSubtype(str, Enum):
    TENDER = "TENDER"
    JOB = "JOB"
    AUCTION = "AUCTION"
    NOTICE = "NOTICE"
    PROPERTY = "PROPERTY"
    OTHER = "OTHER"


class ClassificationSource(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class EditionCreate(BaseModel):
    newspaper_name: str = Field(..., min_length=1, max_length=200)
    edition_date: datetime


class EditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    newspaper_name: str
    edition_date: datetime
    file_hash: str
    total_pages: int
    processed_pages: int = 0
    status: EditionStatus
    current_stage: EditionStage
    archive_status: ArchiveStatus
    archived_at: datetime | None = None
    storage_backend: str
    storage_key: str | None = None
    cover_image_path: str | None = None
    last_error: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class PageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edition_id: int
    page_number: int
    status: PageStatus
    char_count: int
    ocr_used: bool
    error_message: str | None = None
    image_path: str | None = None
    extracted_text: str | None = None
    created_at: datetime


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edition_id: int
    page_id: int | None = None
    page_number: int
    item_type: ItemType
    subtype: ItemSubtype | None = None
    title: str | None = None
    text: str | None = None
    bbox_json: dict | None = None
    extracted_entities_json: dict | None = None
    contact_info_json: dict | None = None
    price_info_json: dict | None = None
    date_info_json: dict | None = None
    location_info_json: dict | None = None
    classification_details_json: dict | None = None
    created_at: datetime


class ItemWithCategoriesResponse(ItemResponse):
    """Item response with categories included."""
    categories: list["ItemCategoryResponse"] = Field(default_factory=list)


class SearchResult(BaseModel):
    item_id: int
    title: str | None = None
    page_number: int
    snippet: str
    highlights: list[str]


class GlobalSearchResult(BaseModel):
    item_id: int
    title: str | None = None
    page_number: int
    snippet: str
    highlights: list[str]
    edition_id: int
    newspaper_name: str
    edition_date: datetime
    item_type: ItemType
    subtype: ItemSubtype | None = None
    categories: list["ItemCategoryResponse"] | None = None


class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    query: str = Field(..., min_length=1)
    item_types: list[ItemType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class SavedSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    query: str
    item_types: list[ItemType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    match_count: int
    last_run: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# User Authentication Schemas

class UserRole(str, Enum):
    READER = "READER"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: UserRole = UserRole.READER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = Field(None, min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_role: UserRole


class TokenData(BaseModel):
    user_id: int | None = None


# Access Request Schemas

class AccessRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AccessRequestCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    organization: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=50)
    reason: str = Field(..., min_length=10)  # Required reason for access
    consent_not_redistribute: bool = False
    # Honeypot field for bot detection - should be empty in real submissions
    website_url: str | None = None


class AccessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    organization: str | None
    phone: str | None
    reason: str
    status: AccessRequestStatus
    consent_not_redistribute: bool
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None
    admin_notes: str | None


class AccessRequestAdminResponse(AccessRequestResponse):
    """Extended response for admin users including internal fields."""
    ip_address: str | None
    user_agent: str | None
    honeypot_field: str | None
    processed_by_user_id: int | None


class AccessRequestUpdate(BaseModel):
    """Admin-only schema for updating access requests."""
    status: AccessRequestStatus
    admin_notes: str | None = None


class HealthResponse(BaseModel):
    status: str


# Public API schemas - for unauthenticated access
class EditionPublicResponse(BaseModel):
    """Public edition information (covers-only access)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    newspaper_name: str
    edition_date: datetime
    status: EditionStatus | None = None
    cover_image_url: str | None = None


class ItemPublicResponse(BaseModel):
    """Public item information (title and preview text only)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    edition_id: int
    page_number: int
    item_type: str
    subtype: str | None = None
    title: str | None = None
    text: str | None = None  # Preview text only (200 chars)


# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    keywords: list[str] = Field(default_factory=list)
    is_active: bool = True
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""
    name: str | None = None
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    keywords: list[str] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CategoryWithStats(CategoryResponse):
    """Category response with additional statistics."""
    item_count: int
    avg_confidence: float | None = None
    recent_items: int = 0  # Items in last 30 days


# Item Category (Classification) Schemas
class ItemCategoryCreate(BaseModel):
    """Schema for manually assigning a category to an item."""
    category_id: int
    confidence: int = Field(default=50, ge=0, le=100)
    notes: str | None = None


class ItemCategoryResponse(BaseModel):
    """Schema for item category response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    category_id: int
    confidence: int
    source: ClassificationSource
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # Include category details
    category: CategoryResponse


# ItemWithCategoriesResponse is defined above (line 89) - use that instead of a duplicate


class ClassificationStats(BaseModel):
    """Statistics about classification results."""
    total_items: int
    items_classified: int
    total_classifications: int
    classification_rate: float  # Percentage of items that have at least one category
    avg_categories_per_item: float


class BatchClassificationRequest(BaseModel):
    """Request for batch classification."""
    item_ids: list[int]
    confidence_threshold: int = Field(default=30, ge=0, le=100)
    clear_existing: bool = True


class BatchClassificationResponse(BaseModel):
    """Response from batch classification."""
    total_items: int
    items_classified: int
    total_classifications: int
    failed_items: list[int] = Field(default_factory=list)
    processing_time: float  # in seconds


# Favorite Schemas
class FavoriteCreate(BaseModel):
    item_id: int
    notes: str | None = None


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    item_id: int
    notes: str | None = None
    created_at: datetime

    # Optional nested Item (if requested)
    item: ItemResponse | None = None


# Collection Schemas
class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_public: bool | None = None


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    color: str
    is_public: bool
    created_at: datetime
    updated_at: datetime


class CollectionItemCreate(BaseModel):
    item_id: int
    notes: str | None = None


class CollectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    item_id: int
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # Nested item details
    item: ItemResponse | None = None


class CollectionWithItemsResponse(CollectionResponse):
    items: list[CollectionItemResponse] = Field(default_factory=list)


# Analytics/Trends Schemas
class TopicTrend(BaseModel):
    category_name: str
    date: datetime
    count: int


class VolumeTrend(BaseModel):
    date: datetime
    count: int


class TrendDashboardResponse(BaseModel):
    topic_trends: list[TopicTrend]
    volume_trends: list[VolumeTrend]
    top_categories: list[dict[str, Any]]  # name, count


# Rebuild models with forward references after all classes are defined
ItemWithCategoriesResponse.model_rebuild()
GlobalSearchResult.model_rebuild()
