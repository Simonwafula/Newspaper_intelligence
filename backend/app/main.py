import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth_routes, categories, editions, export, external, items, processing, public, saved_searches, search, structured_export
from app.db.database import Base, engine
from app.settings import settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Newspaper PDF Intelligence API",
    description="API for processing and searching newspaper PDFs",
    version="1.0.0",
    debug=settings.debug,
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
