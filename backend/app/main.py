import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    admin,
    analytics,
    auth_routes,
    categories,
    collections,
    editions,
    export,
    external,
    favorites,
    items,
    processing,
    public,
    saved_searches,
    search,
    structured_export,
    users,
    webhooks,
)
from app.db.database import Base, engine
from app.settings import settings

# Create database tables
Base.metadata.create_all(bind=engine)

# OpenAPI tags for better documentation organization
tags_metadata = [
    {
        "name": "auth",
        "description": "Authentication endpoints - login, register, and token management",
    },
    {
        "name": "editions",
        "description": "Manage newspaper editions - upload, list, and retrieve edition details",
    },
    {
        "name": "processing",
        "description": "PDF processing operations - trigger extraction and monitor progress",
    },
    {
        "name": "items",
        "description": "Access extracted items - articles, advertisements, and classifieds",
    },
    {
        "name": "search",
        "description": "Full-text search across editions and items with filtering",
    },
    {
        "name": "export",
        "description": "Export data in various formats (CSV, JSON)",
    },
    {
        "name": "structured-export",
        "description": "Export structured data for jobs and tenders with enhanced fields",
    },
    {
        "name": "external-api",
        "description": "External API access with API key authentication for third-party integrations",
    },
    {
        "name": "webhooks",
        "description": "Webhook subscriptions for real-time event notifications",
    },
    {
        "name": "categories",
        "description": "Topic categories for organizing and classifying items",
    },
    {
        "name": "favorites",
        "description": "Bookmark items for later reading",
    },
    {
        "name": "collections",
        "description": "Organize items into named collections for research",
    },
    {
        "name": "analytics",
        "description": "Analytics and trend data across editions",
    },
    {
        "name": "users",
        "description": "User management operations",
    },
    {
        "name": "admin",
        "description": "Administrative operations requiring elevated privileges",
    },
]

app = FastAPI(
    title="Newspaper PDF Intelligence API",
    description="""
## Overview

Newspaper PDF Intelligence transforms newspaper PDFs into searchable, structured data.
Upload newspaper editions to extract articles, advertisements, job listings, and tender notices.

## Key Features

- **PDF Processing**: Upload and extract content from newspaper PDFs using OCR
- **Smart Classification**: Automatic categorization of content into articles, ads, and classifieds
- **Structured Data**: Enhanced extraction for jobs (employer, salary, qualifications) and tenders (issuer, deadline, value)
- **Full-Text Search**: Search across all editions with filtering and highlighting
- **External API**: API key authentication for third-party integrations
- **Webhooks**: Real-time notifications when new content is extracted
- **Export**: Download data as CSV or JSON

## Authentication

Most endpoints require JWT authentication. Obtain a token via `/api/auth/login`.

For external integrations, use API keys generated via `/api/external/keys/generate`.

## Rate Limits

- Standard API: No rate limiting for authenticated users
- External API: Configurable per API key (default: 1000/hour)
    """,
    version="1.0.0",
    debug=settings.debug,
    openapi_tags=tags_metadata,
    contact={
        "name": "Newspaper Intelligence Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (PDFs and page images)
if os.path.exists(settings.storage_path):
    app.mount("/files", StaticFiles(directory=settings.storage_path), name="files")

# Health check endpoint
@app.get("/api/healthz")
async def health_check():
    return {"status": "healthy"}



# Authentication endpoints
app.include_router(auth_routes.router)

# Public endpoints (no authentication required)
app.include_router(public.router)

# Protected endpoints (require authentication)
app.include_router(editions.router, prefix="/api/editions", tags=["editions"])
app.include_router(processing.router, prefix="/api/editions", tags=["processing"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(structured_export.router, prefix="/api/export", tags=["structured-export"])
app.include_router(external.router, prefix="/api", tags=["external-api"])
app.include_router(saved_searches.router, prefix="/api", tags=["saved-searches"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(collections.router, prefix="/api", tags=["collections"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])

# Admin endpoints (require admin role)
app.include_router(admin.router, tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8007,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
