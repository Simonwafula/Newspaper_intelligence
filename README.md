# Newspaper PDF Intelligence

A web application that transforms newspaper PDFs into searchable, structured intelligence. Upload newspaper editions, and the system extracts articles, advertisements, and classifieds using OCR and layout analysis.

## Features

- **PDF Upload & Processing**: Upload newspaper PDFs with automatic text extraction and OCR fallback
- **Smart Content Analysis**: Automatically classify content into stories, ads, and classifieds
- **Searchable Content**: Full-text search across all processed editions
- **Categorized Browsing**: Browse content by type (stories, advertisements, classifieds)
- **REST API**: Complete backend API for integration and testing

## Current Status

✅ **Implemented:**
- Backend FastAPI application with SQLAlchemy models
- PDF processing pipeline with PyMuPDF
- OCR integration with Tesseract (optional)
- Layout analysis and content classification
- Database models for editions, pages, items, and extraction runs
- Complete CRUD API for editions and items
- Full-text search functionality
- React frontend with TypeScript
- File upload and processing interface
- Edition detail view with categorized items
- Responsive UI with modern styling

🔧 **Technical Stack:**
- **Backend**: FastAPI, SQLAlchemy, PyMuPDF, Tesseract
- **Frontend**: React, TypeScript, Vite, TanStack Query
- **Database**: SQLite (development), PostgreSQL (production)
- **Styling**: Custom CSS with responsive design

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Tesseract OCR (optional, for scanned PDFs)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Usage

1. **Upload Edition**: Use the upload form to add newspaper PDFs
2. **Process Content**: Click "Start Processing" to extract and analyze content
3. **Browse Results**: View extracted stories, ads, and classifieds by category
4. **Search Content**: Use the search functionality to find specific content

## API Endpoints

### Editions
- `POST /api/editions/` - Upload new edition
- `GET /api/editions/` - List all editions
- `GET /api/editions/{id}` - Get edition details
- `POST /api/editions/{id}/process` - Start processing
- `POST /api/editions/{id}/reprocess` - Reprocess edition

### Items
- `GET /api/items/edition/{edition_id}/items` - Get items for edition
- `GET /api/items/item/{item_id}` - Get specific item

### Search
- `GET /api/search/edition/{edition_id}/search` - Search within edition
- `GET /api/search/search` - Search across all editions

### Health
- `GET /api/healthz` - Health check

## Configuration

Environment variables (optional):
```bash
DATABASE_URL=sqlite:///./dev.db
STORAGE_PATH=./storage
MAX_PDF_SIZE=50MB
MIN_CHARS_FOR_NATIVE_TEXT=200
OCR_ENABLED=true
OCR_LANGUAGES=eng
DEBUG=false
```

## File Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── db/          # Database configuration
│   └── alembic/          # Database migrations
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Page components
│       ├── services/     # API services
│       └── types/        # TypeScript types
└── storage/             # File storage
```

## Development

### Running Tests
```bash
# Backend
cd backend && python -m pytest

# Frontend
cd frontend && npm test
```

### Code Quality
```bash
# Backend linting
cd backend && ruff check && mypy .

# Frontend linting
cd frontend && npm run lint
```

## License

MIT License