# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Newspaper PDF Intelligence is a web application that transforms newspaper PDFs into searchable, structured intelligence. It uploads newspaper editions and extracts articles, advertisements, and classifieds using OCR and layout analysis.

## Commands

### Development

```bash
# Start both backend and frontend in development mode
make dev

# Start backend only (runs on port 8007)
make dev-backend

# Start frontend only (runs on port 5173)
make dev-frontend
```

### Testing

```bash
# Run all tests
make test

# Run backend tests only
make test-backend
# Or directly: cd backend && PYTHONPATH=$PWD python -m pytest tests/ -v

# Run a single backend test file
cd backend && PYTHONPATH=$PWD python -m pytest tests/test_main.py -v

# Run a single test by name
cd backend && PYTHONPATH=$PWD python -m pytest tests/test_main.py::test_function_name -v
```

### Linting

```bash
# Run all linting
make lint

# Backend linting only
make lint-backend
# Or directly: cd backend && PYTHONPATH=$PWD ruff check .

# Frontend linting only
make lint-frontend
# Or directly: cd frontend && npm run lint
```

### Building

```bash
# Build both for production
make build

# Frontend typecheck and build
cd frontend && npm run typecheck && npm run build
```

### Database Migrations

```bash
# Apply migrations
make db-upgrade
# Or: cd backend && PYTHONPATH=$PWD alembic upgrade head

# Create new migration (replace MSG with description)
make db-create MSG="add_new_field"
# Or: cd backend && PYTHONPATH=$PWD alembic revision --autogenerate -m "add_new_field"
```

## Architecture

### Backend (FastAPI + SQLAlchemy)

The backend is a FastAPI application in `backend/app/`:

- **`main.py`**: Application entry point, mounts routers and static files
- **`settings.py`**: Configuration via pydantic-settings (env vars and `.env` file)
- **`schemas.py`**: Pydantic models for API request/response validation
- **`models/__init__.py`**: SQLAlchemy models (Edition, Page, Item, ExtractionRun, SavedSearch)

**API Routers** (`backend/app/api/`):
- `editions.py`: CRUD for newspaper editions, file upload
- `processing.py`: Trigger and monitor PDF processing
- `items.py`: Get extracted items (stories, ads, classifieds)
- `search.py`: Full-text search within and across editions
- `export.py`: Export functionality
- `saved_searches.py`: Saved search management
- `auth.py`: Admin token authentication

**Services** (`backend/app/services/`):
- `processing_service.py`: Main orchestrator for PDF processing pipeline
- `pdf_processor.py`: PDF text extraction using PyMuPDF
- `ocr_service.py`: Tesseract OCR integration for scanned pages
- `layout_analyzer.py`: Content classification into STORY/AD/CLASSIFIED
- `classifieds_intelligence.py`: Structured data extraction from classifieds
- `saved_search_service.py`: Saved search execution and match counting

**Database**: SQLite for development (`dev.db`), PostgreSQL for production. Migrations in `backend/alembic/`.

### Frontend (React + TypeScript + Vite)

The frontend is a React SPA in `frontend/src/`:

- **`App.tsx`**: Main router setup with react-router-dom
- **`main.tsx`**: Application entry point with QueryClientProvider
- **`services/api.ts`**: Axios-based API client for all backend endpoints
- **`types/index.ts`**: TypeScript type definitions matching backend schemas

**Pages** (`frontend/src/pages/`):
- `EditionsLibrary.tsx`: List/upload editions
- `EditionDetail.tsx`: View edition with categorized items
- `Search.tsx`: Search within a specific edition
- `GlobalSearch.tsx`: Search across all editions
- `SavedSearches.tsx`: Manage saved searches
- `Admin.tsx`: Admin functions (requires ADMIN_TOKEN)

### Data Flow

1. User uploads PDF via frontend → `POST /api/editions/`
2. Backend stores file and creates Edition record with status UPLOADED
3. User triggers processing → `POST /api/editions/{id}/process`
4. ProcessingService extracts pages, runs OCR if needed, analyzes layout
5. Items are classified and stored with type (STORY/AD/CLASSIFIED) and subtype
6. Frontend fetches items via `GET /api/items/edition/{id}/items`

### Authentication

Admin operations (upload, process, delete) require `X-Admin-Token` header matching `ADMIN_TOKEN` env var. Frontend stores token in localStorage.

### Key Environment Variables

```bash
DATABASE_URL=sqlite:///./dev.db    # or postgresql+psycopg://...
STORAGE_PATH=./storage             # PDF and page image storage
ADMIN_TOKEN=your-secret-token      # Required for admin operations
OCR_ENABLED=true                   # Enable Tesseract OCR
OCR_LANGUAGES=eng                  # OCR language codes
```
