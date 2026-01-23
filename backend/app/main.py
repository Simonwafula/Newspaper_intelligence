import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import editions, export, items, processing, public, saved_searches, search, users
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



# Public endpoints (no authentication required)
app.include_router(public.router, prefix="/api/public", tags=["public"])

# Authenticated endpoints
app.include_router(editions.router, prefix="/api/editions", tags=["editions"])
app.include_router(processing.router, prefix="/api/editions", tags=["processing"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(saved_searches.router, prefix="/api", tags=["saved-searches"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8007,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
