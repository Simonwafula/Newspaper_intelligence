# Newspaper PDF Intelligence

A web application that transforms newspaper PDFs into searchable, structured intelligence with role-based access control. Upload newspaper editions, and system extracts articles, advertisements, and classifieds using OCR and layout analysis.

## Features

- **Role-Based Access Control**: Public users see covers only, Readers can search full content, Admins have full access
- **Invite-Based Registration**: No public signup - users must request access and be approved by admins
- **JWT Authentication**: Secure token-based authentication with user roles (READER, ADMIN)
- **PDF Upload & Processing**: Upload newspaper PDFs with automatic text extraction and OCR fallback
- **Smart Content Analysis**: Automatically classify content into stories, ads, and classifieds
- **Searchable Content**: Full-text search across all processed editions
- **Categorized Browsing**: Browse content by type (stories, advertisements, classifieds)
- **Access Request Management**: Admin panel to review and approve access requests

## Access Levels

### Public Access (No Authentication)
- Browse newspaper covers gallery
- View basic edition metadata
- Submit access requests

### Reader Access (Authenticated)
- Full text search and content access
- Save and manage searches
- View all extracted content
- Cannot export or upload content

### Admin Access (Authenticated + Admin Role)
- All Reader capabilities
- Upload and manage editions
- Export data in CSV format
- Manage user accounts
- Approve/deny access requests
- Processing controls and logs

## Current Status

✅ **Implemented:**
- User authentication system with JWT tokens
- Role-based access control (READER/ADMIN)
- Public cover gallery (no authentication required)
- Invite-based access request system with rate limiting
- Protected API endpoints with proper permissions
- Admin management interface
- Backend FastAPI application with SQLAlchemy models
- PDF processing pipeline with PyMuPDF
- OCR integration with Tesseract (optional)
- Layout analysis and content classification
- Database models for users and access requests
- Complete CRUD API for editions and items
- Full-text search functionality
- React frontend with TypeScript
- Responsive UI with modern styling

🔧 **Technical Stack:**
- **Backend**: FastAPI, SQLAlchemy, PyMuPDF, Tesseract
- **Frontend**: React, TypeScript, Vite, TanStack Query
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: JWT tokens with role-based permissions
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
- Frontend: http://localhost:5173
- Backend API: http://localhost:8007
- API Documentation: http://localhost:8007/docs

## Usage

1. **Public Access**: Browse covers gallery at homepage without authentication
2. **Request Access**: Submit access request form for admin approval
3. **Reader Login**: Sign in with approved credentials to access full content
4. **Admin Functions**: Manage users, editions, and access requests
5. **Upload & Process**: Upload PDFs and trigger content extraction
6. **Browse & Search**: View categorized content and use full-text search

## API Endpoints

### Public Endpoints (No Authentication)
- `GET /api/public/editions` - List newspaper editions (covers only)
- `POST /api/public/access-requests` - Submit access request

### Authentication
- `POST /api/auth/login` - Login and receive JWT token
- `GET /api/auth/me` - Get current user information
- `POST /api/auth/logout` - Logout (client-side token removal)

### Reader Endpoints (Authentication Required)
- `GET /api/editions/` - List editions with full details
- `GET /api/editions/{id}` - Get edition with full details
- `GET /api/items/edition/{edition_id}/items` - Get items in edition
- `GET /api/items/item/{item_id}` - Get specific item
- `GET /api/search/edition/{edition_id}/search` - Search within edition
- `GET /api/search/search` - Search across all editions
- `GET /api/saved-searches` - List saved searches
- `POST /api/saved-searches` - Create saved search

### Admin-Only Endpoints (Admin Role Required)
- `POST /api/editions/` - Upload new edition
- `DELETE /api/editions/{id}` - Delete edition
- `POST /api/editions/{id}/process` - Start processing
- `GET /api/export/editions/{id}/export` - Export edition data
- `GET /api/admin/users` - List users
- `POST /api/admin/users` - Create user
- `PUT /api/admin/users/{id}` - Update user
- `DELETE /api/admin/users/{id}` - Delete user
- `GET /api/admin/access-requests` - List access requests
- `PUT /api/admin/access-requests/{id}` - Approve/reject access request

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
OCR_PREPROCESS=true
OCR_PREPROCESS_UNSHARP=true
OCR_PREPROCESS_ADAPTIVE=true
OCR_PREPROCESS_GLOBAL_THRESHOLD=170
OCR_CONFIDENCE_THRESHOLD=55
OCR_RETRY_ENABLED=true
OCR_RETRY_DPI=350
OCR_PSM=3
OCR_RETRY_PSM=4
OCR_FALLBACK_ENABLED=false
OCR_FALLBACK_LANG=en

Optional: install OpenCV for adaptive thresholding in OCR preprocessing:

```bash
pip install opencv-python
```
DEBUG=false

# Authentication (required for production)
SECRET_KEY=your-jwt-secret-key
ADMIN_TOKEN=your-secure-admin-token
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

## Access Control & Security

### User Roles
- **Public**: No authentication, can view covers and submit access requests
- **Reader**: Authenticated user, can read and search all content
- **Admin**: Authenticated with admin role, full system access

### Security Features
- JWT-based authentication with expiration
- Rate limiting on access requests
- Bot protection with honeypot fields
- Role-based API permissions
- Admin token protection for sensitive operations

### Data Access Rules
- Public users see only covers and metadata
- Readers can view all extracted content but cannot export
- Admins can upload, export, and manage users
- All permissions enforced at API and UI levels

## Deployment

### Production Deployment (VPS)

This section covers deploying to a production VPS with systemd.

#### Prerequisites

- Linux server (Ubuntu/CentOS) with sudo access
- PostgreSQL database (recommended for production)
- Domain configured to point to VPS

#### Environment Variables

Required for production:
```bash
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/newspaper_db

# Paths
STORAGE_PATH=/home/newspaper/storage

# Settings
DEBUG=false
SECRET_KEY=your-jwt-secret-key
ADMIN_TOKEN=your-secure-admin-token

# OCR (optional)
OCR_ENABLED=true
OCR_LANGUAGES=eng
OCR_PREPROCESS=true
OCR_CONFIDENCE_THRESHOLD=55
OCR_RETRY_ENABLED=true
OCR_RETRY_DPI=350
OCR_PSM=3
OCR_RETRY_PSM=4
OCR_FALLBACK_ENABLED=false
OCR_FALLBACK_LANG=en

## OCR Accuracy Report (manual compare)
Generate a quick report comparing OCR output to a manual transcription for a page:

```bash
python3 scripts/ocr_accuracy_report.py \
  --db dev.db \
  --edition-id 1 \
  --page-number 1 \
  --manual-text /path/to/manual.txt
```

Batch mode (manual text files in a folder, page number inferred from filename):

```bash
python3 scripts/ocr_accuracy_report.py \
  --db dev.db \
  --edition-id 1 \
  --manual-dir /path/to/manual_texts \
  --csv /path/to/report.csv
```
```

#### Manual Deployment Steps

1. **Setup directories and permissions:**
```bash
mkdir -p /home/newspaper/{storage,logs}
chown -R newspaper:www-data /home/newspaper/{storage,logs}
```

2. **Setup Python environment:**
```bash
cd /home/newspaper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Run database migrations:**
```bash
export PYTHONPATH=/home/newspaper
alembic upgrade head
```

4. **Build frontend:**
```bash
cd frontend
npm install
npm run build
```

5. **Setup systemd service:**
```bash
sudo cp deploy/systemd/newspaper-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newspaper-api
sudo systemctl start newspaper-api
```

#### Service Management

```bash
# Check service status
sudo systemctl status newspaper-api

# View logs
sudo journalctl -u newspaper-api -f

# Restart service
sudo systemctl restart newspaper-api
```

## Security Considerations

1. **Enable HTTPS:** Always use SSL/TLS in production
2. **Firewall:** Configure firewall to only allow necessary ports
3. **Admin Token:** Use a strong, random `ADMIN_TOKEN`
4. **JWT Secret:** Use a secure, random `SECRET_KEY`
5. **Database Security:** Use strong passwords and limit database access
6. **File Permissions:** Ensure storage directories are not web-accessible
7. **Regular Updates:** Keep dependencies and system packages updated

## License

MIT License
