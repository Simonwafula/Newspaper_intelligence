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

## Deployment

### Production Deployment (VPS)

This section covers deploying to a production VPS with OpenLiteSpeed and systemd.

#### Prerequisites

- Linux server (Ubuntu/CentOS) with sudo access
- OpenLiteSpeed web server with CyberPanel
- Python 3.8+ and Node.js 16+
- PostgreSQL database (recommended for production)
- Domain configured to point to the VPS

#### Quick Deploy

1. **Clone the repository:**
```bash
git clone <your-repo-url> /home/mag.mstatilitechnologies.com/public_html
cd /home/mag.mstatilitechnologies.com/public_html
```

2. **Configure environment:**
```bash
# Create environment file
cp .env.example .env
# Edit .env with production settings
```

3. **Run the deployment script:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

#### Manual Deployment Steps

1. **Setup directories and permissions:**
```bash
# Create required directories
mkdir -p /home/mag.mstatilitechnologies.com/{storage,logs}
chown -R magms2596:magms2596 /home/mag.mstatilitechnologies.com/{storage,logs}
```

2. **Setup Python environment:**
```bash
cd /home/mag.mstatilitechnologies.com
python3 -m venv .venv
source .venv/bin/activate
cd public_html/backend
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
# Create /home/mag.mstatilitechnologies.com/.env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname
STORAGE_PATH=/home/mag.mstatilitechnologies.com/storage
LOG_PATH=/home/mag.mstatilitechnologies.com/logs
DEBUG=false
ADMIN_TOKEN=your-secure-admin-token
OCR_ENABLED=true
OCR_LANGUAGES=eng
```

4. **Run database migrations:**
```bash
cd /home/mag.mstatilitechnologies.com/public_html/backend
export PYTHONPATH=/home/mag.mstatilitechnologies.com/public_html
alembic upgrade head
```

5. **Build frontend:**
```bash
cd /home/mag.mstatilitechnologies.com/public_html/frontend
npm install
npm run build
```

6. **Setup systemd service:**
```bash
# Copy service template
sudo cp deploy/systemd/mag-newspaper-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mag-newspaper-api
sudo systemctl start mag-newspaper-api
```

7. **Configure OpenLiteSpeed:**
   - Set up reverse proxy from `/` and `/api` to `http://127.0.0.1:8000`
   - Configure static file serving for `frontend/dist`
   - Enable HTTPS with SSL certificate

#### Environment Variables

Required for production:
```bash
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/newspaper_db

# Paths
STORAGE_PATH=/home/mag.mstatilitechnologies.com/storage
LOG_PATH=/home/mag.mstatilitechnologies.com/logs

# Settings
DEBUG=false
ADMIN_TOKEN=your-secure-token-here

# OCR (optional)
OCR_ENABLED=true
OCR_LANGUAGES=eng
```

#### Service Management

```bash
# Check service status
sudo systemctl status mag-newspaper-api

# View logs
sudo journalctl -u mag-newspaper-api -f

# Restart service
sudo systemctl restart mag-newspaper-api

# Stop service
sudo systemctl stop mag-newspaper-api
```

#### Troubleshooting

**Service won't start:**
```bash
# Check service status for errors
sudo systemctl status mag-newspaper-api

# Check detailed logs
sudo journalctl -u mag-newspaper-api -n 50

# Check environment file
cat /home/mag.mstatilitechnologies.com/.env
```

**Database connection issues:**
```bash
# Test database connection
psql $DATABASE_URL

# Check if migrations ran
cd /home/mag.mstatilitechnologies.com/public_html/backend
alembic current
```

**Permission issues:**
```bash
# Fix storage permissions
sudo chown -R magms2596:magms2596 /home/mag.mstatilitechnologies.com/storage
sudo chmod -R 755 /home/mag.mstatilitechnologies.com/storage
```

**OpenLiteSpeed proxy issues:**
- Check OLS error logs: `/usr/local/lsws/logs/error.log`
- Verify backend is accessible: `curl http://127.0.0.1:8000/api/healthz`
- Check proxy configuration in CyberPanel

#### Security Considerations

1. **Enable HTTPS:** Always use SSL/TLS in production
2. **Firewall:** Configure firewall to only allow necessary ports
3. **Admin Token:** Use a strong, random `ADMIN_TOKEN`
4. **Database Security:** Use strong passwords and limit database access
5. **File Permissions:** Ensure storage directories are not web-accessible
6. **Regular Updates:** Keep dependencies and system packages updated

#### Performance Optimization

1. **Database:** Add indexes for frequently queried fields
2. **Caching:** Consider Redis for session storage and caching
3. **CDN:** Use CDN for static assets in production
4. **Monitoring:** Set up monitoring for service health and performance

## License

MIT License