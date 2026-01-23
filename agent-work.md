# Newspaper PDF Intelligence - Project Plan

## Agent Behavior Instructions

### Primary Directives
1. **Always read this file first** at the start of any session to understand current state
2. **Update completion logs** immediately after finishing any task or subtask
3. **Run verification tests** before marking tasks complete
4. **Document blockers** and unknowns clearly for future sessions
5. **Maintain consistency** in file naming, code style, and documentation

### Session Start Protocol
1. Read this entire file to understand current state
2. Check recent completion logs below
3. Identify next logical task based on dependencies
4. Update todo list before starting work

### Task Completion Protocol
- Mark status as DONE only after verification
- Update any dependent tasks
- Commit changes to git with descriptive messages

### Git Workflow Protocol
- Commit after completing major features or fixes
- Use descriptive commit messages following project conventions
- Push to remote after significant milestones
- Check git status before starting new work
- Pull latest changes before starting new sessions

### Status Emojis
- ✅ DONE
- 🔄 IN_PROGRESS
- 🚫 BLOCKED
- 📋 TODO

---

## Project Status Overview

| Phase | Status | Description |
|-------|--------|-------------|
| MVP Core | ✅ DONE | Upload, process, search, export |
| Authentication | ✅ DONE | JWT auth, role-based access, route guards |
| Phase 2 Features | 📋 TODO | Topics, analytics, collections |

---

## Project Goal

Build a web application that transforms newspaper PDFs into searchable, structured intelligence. Users upload newspaper editions, and the system extracts articles, advertisements, and classifieds using OCR and layout analysis. The platform makes historical newspapers searchable and exportable, focusing on reliability and accuracy over complex ML models.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Storage       │
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

Authentication Flow:
Login → JWT Token → AuthContext → ProtectedRoute → API calls with Bearer token
```

---

## MVP Demo Script

### Setup
```bash
git clone <repo-url>
cd Newspaper_intelligence
make dev  # Starts both backend and frontend
```

### Demo Flow
1. **Upload Newspaper** - Navigate to Admin, upload PDF, show processing progress
2. **Review Extraction** - View edition detail, show items (articles, ads, classifieds)
3. **Search & Export** - Use global search, apply filters, export to CSV
4. **Reprocess** - Click reprocess button, show real-time progress

### Key Demo Points
- **Reliability**: Consistent extraction across PDF types
- **Speed**: Quick processing and responsive UI
- **Accuracy**: Proper classification of items
- **Export**: Clean, structured CSV output
- **Search**: Fast full-text search with highlighting

### Sample Data
- Include 2-3 sample newspaper PDFs of varying quality
- One with good native text, one requiring OCR
- Different layouts and content types

---

## Decisions & Assumptions

1. **Database**: SQLite for development, PostgreSQL for production - SQLAlchemy for compatibility
2. **OCR Strategy**: Tesseract as fallback when native PDF text is insufficient
3. **Processing Model**: Synchronous processing for MVP - simpler architecture, easier to debug
4. **Storage**: Local filesystem - simpler than cloud storage for MVP
5. **Frontend**: React with TypeScript - good balance of development speed and type safety
6. **PDF Processing**: PyMuPDF - mature, good Python support, reasonable licensing
7. **Authentication**: JWT tokens with role-based access (READER/ADMIN)

---

## COMPLETED WORK ✅

### MVP Foundation (Completed)
- [x] Project infrastructure and tooling
- [x] Backend (FastAPI + SQLAlchemy)
- [x] Database models and migrations (Edition, Page, Item, ExtractionRun, SavedSearch)
- [x] PDF processing pipeline (PyMuPDF + Tesseract OCR)
- [x] Layout analysis and item extraction
- [x] Full CRUD API for editions, items, search
- [x] CSV export functionality
- [x] Frontend (React + TypeScript + Vite)
- [x] All core UI pages and components
- [x] Cross-edition global search with filters
- [x] Saved searches with match counts
- [x] Processing UX with progress tracking
- [x] Deployment tooling (systemd, scripts)
- [x] Linting, testing, CI/CD setup

### Authentication System (Completed 2026-01-23)
- [x] User model with READER/ADMIN roles
- [x] JWT token authentication (bcrypt password hashing)
- [x] Login/logout endpoints (`/api/auth/login`, `/api/auth/me`)
- [x] Frontend AuthContext for centralized state management
- [x] ProtectedRoute component for route guards
- [x] API client with JWT interceptors (automatic Bearer token)
- [x] 401 handling with auto-redirect to login
- [x] Role-based admin access (Admin page requires ADMIN role)
- [x] Removed legacy admin token system

**Key Files:**
- `backend/app/api/auth.py` - JWT auth functions
- `backend/app/api/auth_routes.py` - Auth endpoints
- `backend/app/models/__init__.py` - User model
- `frontend/src/context/AuthContext.tsx` - Auth state management
- `frontend/src/components/ProtectedRoute.tsx` - Route guards
- `frontend/src/services/api.ts` - JWT in API calls

---

## TODO - Phase 2 Features 📋

### Phase 2A: Core Intelligence (HIGH Priority)

#### Topic Categories & Auto-Tagging
**Status:** 📋 TODO
**Purpose:** Foundation for filtering/browsing by topic
**Tasks:**
- [ ] Category model with predefined topics (Economics, Politics, Labor, Business, etc.)
- [ ] Auto-classification service (keyword-based with confidence scoring)
- [ ] Category API endpoints
- [ ] Category filter UI on search/browse pages
- [ ] Category badges on items

#### Structured Classifieds Enhancement
**Status:** 📋 TODO
**Purpose:** Structured data extraction for labor market analysis
**Tasks:**
- [ ] Enhanced parsing for jobs (employer, salary, qualifications, location)
- [ ] Enhanced parsing for tenders (issuer, deadline, value, category)
- [ ] Structured export endpoints (JSON/CSV)
- [ ] Rich display cards for jobs/tenders

#### REST API for External Apps
**Status:** 📋 TODO
**Purpose:** Enable external integrations
**Tasks:**
- [ ] API key authentication system
- [ ] Rate limiting
- [ ] Webhook support for new data events
- [ ] OpenAPI documentation enhancement

### Phase 2B: User Features (MEDIUM Priority)

#### Favorites & Bookmarks
- [ ] Bookmark items for later reading
- [ ] Favorites list page

#### Collections & Research Projects
- [ ] Named collections of items
- [ ] Notes/annotations on items
- [ ] Export collections with citations

#### Trend Dashboard
- [ ] Topic frequency over time
- [ ] Volume trends charts
- [ ] Word cloud / emerging terms

### Phase 2C: Advanced Features (LOW Priority)

- [ ] Smart Alerts (email/webhook notifications for saved searches)
- [ ] Entity Extraction (organizations, people, locations)
- [ ] Reading History
- [ ] Citation Export (APA, BibTeX)

---

## Reality Check / Ground Truth

### Python Version Guidance
**Critical for Mac Intel users**: PyMuPDF build issues are common on newer Python versions.
- **Recommended**: Python 3.11 for development
- **Avoid**: Python 3.12+ on Mac Intel due to PyMuPDF compilation failures

```bash
python --version  # Should be 3.11.x
pip list | grep pymupdf  # Verify installation
```

### Tesseract Dependency
**Required for OCR functionality** - system-level dependency not managed by pip.

```bash
# macOS
brew install tesseract
brew install tesseract-lang  # Additional languages

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng

# Verify
tesseract --version
```

### Database Search Differences

| Feature | SQLite (Dev) | PostgreSQL (Prod) |
|---------|--------------|-------------------|
| Full-text | FTS5 virtual tables | tsvector + GIN indexes |
| Query syntax | `MATCH 'term'` | `@@ to_tsquery('term')` |
| Stemming | No | Yes |
| Ranking | Basic | Advanced relevance |

---

## Extraction Limitations

### OCR Accuracy
- **Best**: Clean 300+ DPI, simple fonts, high contrast → 80-95% accuracy
- **Poor**: Low resolution, decorative fonts, multi-column → 60-80% accuracy

### Layout Analysis Limitations
- Complex multi-column layouts may merge/split incorrectly
- Advertisement classification based on font size heuristics
- Dense classified text blocks are challenging

### Classification Accuracy Rates
- **Articles**: 85-90% correctly identified
- **Advertisements**: 75-80%
- **Classifieds**: 70-75%
- **Tenders/Notices**: 60-70% (keyword-dependent)

### Processing Times
- **Text-native PDF**: ~2-5 seconds per page
- **OCR-required PDF**: ~10-30 seconds per page
- **Large editions**: 5-15 minutes total

### Data Quality Issues
**Common problems requiring manual review:**
- Encoding errors with special characters and non-ASCII text
- Table extraction with misaligned columnar data
- Image captions frequently separated from images
- "Continued on page X" not properly linked

**Quality assurance recommendations:**
- Spot-check extraction results after processing
- Implement confidence scoring for extracted items
- Provide manual correction interface for critical data
- Log extraction quality metrics for monitoring

---

## Performance Considerations

- Large PDFs processed page-by-page to avoid memory issues
- Database indexes on searchable fields
- File serving uses streaming for large files
- Frontend implements virtual scrolling for large result sets
- Single-threaded extraction per edition (concurrent processing TODO)
- FTS search may slow with >100k items

---

## Security Notes

- File upload validation (PDF only, size limits)
- Safe file serving with path traversal protection
- SQL injection prevention via SQLAlchemy ORM
- CORS configuration for allowed origins
- Input sanitization for search queries
- JWT tokens for authentication (30-day expiry)
- Role-based access control (READER/ADMIN)
- Passwords hashed with bcrypt

---

## Operational Runbook

### Development Setup
```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8007

# Frontend
cd frontend
npm install
npm run dev
```

### Quick Commands (Makefile)
```bash
make dev              # Start both frontend + backend
make dev-backend      # Backend only (port 8007)
make dev-frontend     # Frontend only (port 5173)
make test             # Run all tests
make lint             # Run all linting
make build            # Build for production
make db-upgrade       # Apply migrations
make db-create MSG="description"  # Create migration
```

### Git Workflow
```bash
git status                    # Check before starting
git pull origin main          # Get latest
git add .                     # Stage changes
git commit -m "message"       # Commit
git push origin main          # Push after milestones
```

### Troubleshooting

**OCR Issues:**
- Tesseract not found → `brew install tesseract`
- Wrong language → Set `OCR_LANGUAGES=eng+fra`
- Poor accuracy → Check image resolution

**Search Issues:**
- No results → Check FTS tables populated
- Slow → Add indexes, use pagination

**Auth Issues:**
- 401 errors → Check JWT token in localStorage
- Token expired → Re-login
- Admin access denied → Verify user has ADMIN role

---

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./dev.db    # or postgresql://...

# Storage
STORAGE_PATH=./storage

# JWT Authentication
SECRET_KEY=your-secret-key-here    # Required for JWT signing

# Processing
OCR_ENABLED=true
OCR_LANGUAGES=eng
MAX_PDF_SIZE=50MB

# Development
DEBUG=false
LOG_LEVEL=INFO
```

---

## Session Log

### 2026-01-23: JWT Authentication Implementation
**Tasks Completed:**
- Wired JWT into frontend API client with axios interceptors
- Created AuthContext for centralized auth state management
- Added ProtectedRoute component for route guards
- Updated Admin page to use JWT (removed legacy token login form)
- Updated AuthenticatedHeader to use AuthContext
- Fixed LoginPage to use AuthContext login function
- Removed legacy admin_token from backend settings
- Removed verify_admin_token function from backend
- All frontend linting/typecheck passing

**Files Modified:**
- `frontend/src/context/AuthContext.tsx` (new)
- `frontend/src/components/ProtectedRoute.tsx` (new)
- `frontend/src/services/api.ts`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/Admin.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/AuthenticatedHeader.tsx`
- `frontend/src/types/index.ts`
- `backend/app/api/auth.py`
- `backend/app/settings.py`
- `frontend/.env`

---

## Task Update Template

When updating any task status, use this format:

```markdown
### [Task Name] [Status Emoji]
**Status:** [DONE/IN_PROGRESS/BLOCKED/TODO]
**DoD:** [Clear acceptance criteria]
**Files touched:** [List of files modified]
**Verification:** [How to verify completion]
**Completed:** [YYYY-MM-DD] (if done)
**Notes:** [Additional context]
```
