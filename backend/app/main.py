from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.settings import settings
from app.db.database import engine, Base

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

# Import routes
from app.api import editions, processing, items, search

app.include_router(editions.router, prefix="/api/editions", tags=["editions"])
app.include_router(processing.router, prefix="/api/editions", tags=["processing"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )