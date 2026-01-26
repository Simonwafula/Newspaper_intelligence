# Setup Guide

This guide covers initial setup of the Newspaper Intelligence application.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Tesseract OCR (optional, for scanned PDFs)

## Quick Start

```bash
# 1. Install dependencies
make install-backend
make install-frontend

# 2. Run database migrations and seed data
make seed-all

# 3. Start development servers
make dev
```

## Database Setup

### Run Migrations

```bash
make db-upgrade
```

### Create New Migration

```bash
make db-create MSG="description_of_changes"
```

## Creating Users

### Create Admin User

The first admin user must be created via the seed script:

```bash
# Create default admin (admin@newspaper-intel.local / changeme123!)
make seed-admin

# Create admin with custom credentials
make seed-admin ARGS="--email admin@yourcompany.com --password YourSecurePassword123"

# Or run directly with all options
cd backend
PYTHONPATH=$PWD python -m app.services.seed_users \
  --email admin@yourcompany.com \
  --password YourSecurePassword123 \
  --name "Admin Name"
```

**Important:** Change the default password immediately after first login!

### Create Regular Users

Once an admin exists, regular users can be created via:

1. **Admin Panel** (`/app/admin`) - Admin can create users directly
2. **Access Request** (`/request-access`) - Users request access, admin approves

## Seeding Categories

Seed the default topic categories for content classification:

```bash
make seed-categories
```

## Complete Initial Setup

Run all setup steps at once:

```bash
make seed-all
```

This runs:
1. Database migrations (`db-upgrade`)
2. Admin user creation (`seed-admin`)
3. Category seeding (`seed-categories`)

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database (default: SQLite for development)
DATABASE_URL=sqlite:///./dev.db

# For PostgreSQL in production:
# DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/newspaper_intel

# Storage path for uploaded PDFs
STORAGE_PATH=./storage

# JWT Secret (IMPORTANT: Set a unique value in production!)
SECRET_KEY=your-secret-key-here

# OCR Settings
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

# Optional: PaddleOCR fallback
# pip install paddleocr

# Optional: OpenCV for adaptive thresholding
# pip install opencv-python

# CORS (add your frontend URL in production)
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Access Request Workflow

The application supports an access request workflow:

1. **User requests access** at `/request-access`
   - Fills in name, email, organization, reason
   - Request is stored with `PENDING` status

2. **Admin reviews request** at `/app/admin`
   - Can approve or reject with notes
   - Approved requests automatically create a user account

3. **User receives credentials**
   - Currently: Admin must manually communicate credentials
   - Default temporary password: `temp123456`
   - User should change password after first login

> **Note:** Email notifications are not yet configured. Admin must manually notify users of their account credentials.

## Available Make Commands

```bash
make help              # Show all available commands

# Development
make dev               # Start backend + frontend
make dev-backend       # Start backend only (port 8007)
make dev-frontend      # Start frontend only (port 5173)

# Database & Seeding
make db-upgrade        # Run migrations
make db-create MSG=x   # Create new migration
make seed-admin        # Create admin user
make seed-categories   # Seed topic categories
make seed-all          # All of the above

# Quality
make lint              # Run all linting
make test              # Run all tests

# Building
make build             # Build for production
make ci                # Full CI pipeline
```

## Troubleshooting

### "No admin user exists"

Run `make seed-admin` to create the first admin user.

### "Module not found" errors

Ensure you're running commands from the project root with proper PYTHONPATH:

```bash
cd backend
PYTHONPATH=$PWD python -m app.services.seed_users
```

### Database errors

Reset the database (development only):

```bash
rm backend/dev.db
make db-upgrade
make seed-all
```

### OCR not working

Install Tesseract OCR:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng

# Verify installation
tesseract --version
```
