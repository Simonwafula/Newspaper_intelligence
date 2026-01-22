from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    item_id: int
    title: str | None = None
    page_number: int
    snippet: str
    highlights: list[str]


class HealthResponse(BaseModel):
    status: str
