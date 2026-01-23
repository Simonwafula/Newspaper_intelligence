from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class EditionStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
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


class EditionCreate(BaseModel):
    newspaper_name: str = Field(..., min_length=1, max_length=200)
    edition_date: datetime


class EditionResponse(BaseModel):
    id: int
    newspaper_name: str
    edition_date: datetime
    file_hash: str
    num_pages: int
    status: EditionStatus
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None

    class Config:
        from_attributes = True


class PageResponse(BaseModel):
    id: int
    edition_id: int
    page_number: int
    image_path: str | None = None
    extracted_text: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemResponse(BaseModel):
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

    class Config:
        from_attributes = True


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


class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    query: str = Field(..., min_length=1)
    item_types: list[ItemType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class SavedSearchResponse(BaseModel):
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

    class Config:
        from_attributes = True


# User Authentication Schemas

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = Field(None, min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: int | None = None


class HealthResponse(BaseModel):
    status: str


# Public API schemas - for unauthenticated access
class EditionPublicResponse(BaseModel):
    """Public edition information (covers-only access)."""
    id: int
    newspaper_name: str
    edition_date: datetime
    num_pages: int
    status: str

    class Config:
        from_attributes = True


class ItemPublicResponse(BaseModel):
    """Public item information (title and preview text only)."""
    id: int
    edition_id: int
    page_number: int
    item_type: str
    subtype: str | None = None
    title: str | None = None
    text: str | None = None  # Preview text only (200 chars)

    class Config:
        from_attributes = True
