# Newspaper PDF Intelligence - Project Plan

## Project Goal

Build a web application that transforms newspaper PDFs into searchable, structured intelligence. Users upload newspaper editions, and the system extracts articles, advertisements, and classifieds using OCR and layout analysis. The platform makes historical newspapers searchable and exportable, focusing on reliability and accuracy over complex ML models.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Storage      │
│   React+Vite    │◄──►│   FastAPI       │◄──►│   Local FS      │
│   TypeScript    │    │   Python        │    │   PDFs/Imgs     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   SQLite/PG     │
                       │   SQLAlchemy    │
                       └─────────────────┘

Processing Pipeline:
Upload → Validate → Store → Extract Text → OCR (if needed) → Layout Analysis → Item Extraction → Index
```

## TODO Backlog

### 1. Project Infrastructure ✅
**Status:** DONE  
**DoD:** Directory structure created, gitignore in place  
**Files touched:** `/`, `.gitignore`, `storage/.gitkeep`  
**Verification:** Project structure exists

### 2. Backend Foundation
**Status:** IN_PROGRESS  
**DoD:** FastAPI app with basic structure, dependencies configured  
**Files touched:** `backend/requirements.txt`, `backend/app/main.py`, `backend/app/settings.py`  
**Verification:** `uvicorn app.main:app --reload` starts successfully  
**Risk/Unknowns:** None  

#### 2.1 Database Models
**Status:** TODO  
**DoD:** SQLAlchemy models for Edition, Page, Item, ExtractionRun  
**Files touched:** `backend/app/models/`  
**Verification:** Models create tables without errors  
**Risk/Unknowns:** FTS5 vs tsvector compatibility  

#### 2.2 Database Migrations
**Status:** TODO  
**DoD:** Alembic configured, initial migration created  
**Files touched:** `backend/alembic/`  
**Verification:** `alembic upgrade head` works on both SQLite and PostgreSQL  
**Risk/Unknowns:** PostgreSQL-specific features in SQLite  

### 3. PDF Processing Pipeline
**Status:** TODO  
**DoD:** PDF upload, text extraction, OCR fallback, layout analysis  
**Files touched:** `backend/app/services/`, `backend/app/api/editions.py`  
**Verification:** Can process a PDF and store extracted content  
**Risk/Unknowns:** Tesseract installation, OCR accuracy  

#### 3.1 PDF Upload & Storage
**Status:** TODO  
**DoD:** File upload endpoint, validation, deduplication  
**Files touched:** `backend/app/api/editions.py`  
**Verification:** Upload works, duplicate prevention works  
**Risk/Unknowns:** Large file handling  

#### 3.2 Text Extraction
**Status:** TODO  
**DoD:** PyMuPDF integration, selective OCR  
**Files touched:** `backend/app/services/pdf_processor.py`  
**Verification:** Extracts text from both native and scanned PDFs  
**Risk/Unknowns:** Memory usage with large PDFs  

#### 3.3 Layout Analysis & Item Extraction
**Status:** TODO  
**DoD:** Headline detection, content grouping, classification  
**Files touched:** `backend/app/services/layout_analyzer.py`  
**Verification:** Identifies stories, ads, classifieds with reasonable accuracy  
**Risk/Unknowns:** Layout complexity, font analysis availability  

### 4. API Development
**Status:** TODO  
**DoD:** Full CRUD API for editions, items, search, export  
**Files touched:** `backend/app/api/`  
**Verification:** All endpoints documented with Swagger, return correct data  
**Risk/Unknowns:** Search performance with large datasets  

#### 4.1 Editions API
**Status:** TODO  
**DoD:** POST /api/editions, GET /api/editions, GET /api/editions/{id}  
**Files touched:** `backend/app/api/editions.py`  
**Verification:** Can upload, list, and retrieve editions  

#### 4.2 Search API
**Status:** TODO  
**DoD:** GET /api/editions/{id}/search with full-text search  
**Files touched:** `backend/app/api/search.py`  
**Verification:** Search returns relevant results with highlights  

#### 4.3 Export API
**Status:** TODO  
**DoD:** GET /api/editions/{id}/export/classifieds.csv  
**Files touched:** `backend/app/api/export.py`  
**Verification:** CSV downloads with proper headers  

### 5. Frontend Development
**Status:** TODO  
**DoD:** React app with Vite, TypeScript, routing, UI components  
**Files touched:** `frontend/`  
**Verification:** App builds and runs locally  
**Risk/Unknowns:** PDF.js integration complexity  

#### 5.1 Frontend Setup
**Status:** TODO  
**DoD:** Vite + React + TypeScript project configured  
**Files touched:** `frontend/package.json`, `frontend/vite.config.ts`  
**Verification:** `npm run dev` starts development server  

#### 5.2 Core UI Components
**Status:** TODO  
**DoD:** Editions library, edition detail, item lists, PDF viewer  
**Files touched:** `frontend/src/components/`, `frontend/src/pages/`  
**Verification:** UI renders without errors, basic navigation works  

#### 5.3 Search & Export UI
**Status:** TODO  
**DoD:** Search interface with highlighting, CSV export functionality  
**Files touched:** `frontend/src/pages/Search.tsx`, `frontend/src/pages/EditionDetail.tsx`  
**Verification:** Search works, export downloads file  

### 6. Development Tooling & Quality
**Status:** TODO  
**DoD:** Linters, tests, CI configuration  
**Files touched:** `backend/pyproject.toml`, `frontend/eslint.config.js`, `Makefile`  
**Verification:** All linting passes, tests run, build succeeds  
**Risk/Unknowns:** Test coverage vs development speed trade-off  

### 7. Documentation & Deployment
**Status:** TODO  
**DoD:** README, setup instructions, deployment notes  
**Files touched:** `README.md`, `Makefile`  
**Verification:** New developer can setup and run the project locally  

## Decisions & Assumptions

1. **Database Choice**: SQLite for development, PostgreSQL for production - uses SQLAlchemy for compatibility
2. **OCR Strategy**: Tesseract as fallback when native PDF text is insufficient - balances reliability and accuracy
3. **Processing Model**: Synchronous processing acceptable for MVP - simpler architecture, easier to debug
4. **Storage**: Local filesystem - simpler than cloud storage for MVP, easier to migrate later
5. **Frontend**: React with TypeScript - good balance of development speed and type safety
6. **PDF Processing**: PyMuPDF over alternatives - mature, good Python support, reasonable licensing

## Known Issues / Bugs

- None yet - project is just starting

## Operational Runbook

### Development Setup
```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Database
alembic upgrade head
```

### PDF Processing Workflow
1. User uploads PDF via frontend
2. Backend validates PDF, computes hash, checks for duplicates
3. PDF stored in `storage/editions/`
4. Processing starts: extract text → OCR if needed → layout analysis → item extraction
5. Results stored in database, status updated to READY
6. Frontend polls status until completion

### OCR Troubleshooting
- **Tesseract not found**: Install system package (`brew install tesseract` on macOS)
- **Wrong language**: Set `OCR_LANGUAGES` env var (e.g., `eng+fra`)
- **Poor accuracy**: Check image resolution, try preprocessing
- **Memory issues**: Reduce `MAX_PDF_SIZE` or process page-by-page

### Search Issues
- **No results**: Check FTS tables are populated, run search manually in DB
- **Slow search**: Add indexes, consider pagination for large results
- **Encoding issues**: Ensure UTF-8 handling throughout pipeline

### File Serving Security
- All file access goes through controlled endpoints
- Path traversal prevented by validating file IDs against database
- PDFs served with appropriate MIME types and CORS headers

## Environment Variables

```bash
# Database (required)
DATABASE_URL=sqlite:///./dev.db  # or postgresql+psycopg://...

# Storage (optional, defaults to ./storage)
STORAGE_PATH=./storage

# Processing (optional)
MAX_PDF_SIZE=50MB
MIN_CHARS_FOR_NATIVE_TEXT=200
OCR_ENABLED=true
OCR_LANGUAGES=eng

# Development (optional)
DEBUG=true
LOG_LEVEL=INFO
```

## Performance Considerations

- Large PDFs processed page-by-page to avoid memory issues
- Database indexes on searchable fields
- File serving uses streaming for large files
- Frontend implements virtual scrolling for large result sets

## Security Notes

- File upload validation (PDF only, size limits)
- Safe file serving with path traversal protection
- SQL injection prevention via SQLAlchemy ORM
- Basic CORS configuration for development
- Input sanitization for search queries