from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


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

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    edition = relationship("Edition", back_populates="items")
    page = relationship("Page", back_populates="items")


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
