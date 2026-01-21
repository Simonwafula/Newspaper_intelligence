from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


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
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PageResponse(BaseModel):
    id: int
    edition_id: int
    page_number: int
    image_path: Optional[str] = None
    extracted_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemResponse(BaseModel):
    id: int
    edition_id: int
    page_id: Optional[int] = None
    page_number: int
    item_type: ItemType
    subtype: Optional[ItemSubtype] = None
    title: Optional[str] = None
    text: Optional[str] = None
    bbox_json: Optional[dict] = None
    extracted_entities_json: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    item_id: int
    title: Optional[str] = None
    page_number: int
    snippet: str
    highlights: List[str]


class HealthResponse(BaseModel):
    status: str