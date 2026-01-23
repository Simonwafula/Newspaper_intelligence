# Newspaper Intelligence - Makefile
# Provides convenient commands for development, testing, and building

.PHONY: help dev lint test clean install-backend install-frontend build-backend build-frontend build ci check-deps

# Default target
help:
	@echo "Newspaper Intelligence - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev              - Start both backend and frontend in development mode"
	@echo "  dev-backend      - Start backend only (uvicorn)"
	@echo "  dev-frontend     - Start frontend only (vite)"
	@echo ""
	@echo "Quality:"
	@echo "  lint             - Run linting for both backend and frontend"
	@echo "  lint-backend      - Run ruff linting on backend"
	@echo "  lint-frontend     - Run eslint on frontend"
	@echo "  test             - Run tests for both backend and frontend"
	@echo "  test-backend      - Run pytest on backend"
	@echo "  test-frontend     - Run test commands for frontend"
	@echo ""
	@echo "Building:"
	@echo "  build            - Build both backend and frontend for production"
	@echo "  build-backend     - Build backend (dependencies + lint + test)"
	@echo "  build-frontend    - Build frontend (typecheck + vite build)"
	@echo ""
	@echo "Database & Seeding:"
	@echo "  db-upgrade       - Run database migrations"
	@echo "  db-create MSG=x  - Create new migration with message"
	@echo "  seed-admin       - Create admin user (use ARGS for custom email/password)"
	@echo "  seed-categories  - Seed default topic categories"
	@echo "  seed-all         - Run migrations + seed admin + seed categories"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            - Clean build artifacts and cache"
	@echo "  install-backend   - Install backend Python dependencies"
	@echo "  install-frontend  - Install frontend Node.js dependencies"
	@echo "  check-deps       - Check if required system dependencies are installed"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci               - Run full CI pipeline (lint + test + build)"

# Development commands
dev:
	@echo "Starting backend and frontend in development mode..."
	@make -j2 dev-backend dev-frontend

dev-backend:
	@echo "Starting backend development server..."
	@cd backend && PYTHONPATH=$$PWD uvicorn app.main:app --reload --host 0.0.0.0 --port 8007

dev-frontend:
	@echo "Starting frontend development server..."
	@cd frontend && npm run dev

# Quality commands
lint: lint-backend lint-frontend

lint-backend:
	@echo "Running backend linting..."
	@cd backend && PYTHONPATH=$$PWD ruff check .

lint-frontend:
	@echo "Running frontend linting..."
	@cd frontend && npm run lint

test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	@cd backend && PYTHONPATH=$$PWD python -m pytest tests/ -v

test-frontend:
	@echo "Running frontend tests..."
	@cd frontend && npm test || echo "No frontend tests configured"

# Building commands
build: build-backend build-frontend

build-backend:
	@echo "Building backend for production..."
	@cd backend && PYTHONPATH=$$PWD ruff check . && PYTHONPATH=$$PWD python -m pytest tests/ -v

build-frontend:
	@echo "Building frontend for production..."
	@cd frontend && npm run typecheck && npm run build

# Maintenance commands
clean:
	@echo "Cleaning build artifacts..."
	@cd backend && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@cd backend && find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@cd backend && find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@cd frontend && rm -rf dist node_modules/.vite 2>/dev/null || true
	@echo "Clean completed"

install-backend:
	@echo "Installing backend dependencies..."
	@cd backend && python -m pip install -r requirements.txt
	@echo "Backend dependencies installed"

install-frontend:
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Frontend dependencies installed"

check-deps:
	@echo "Checking system dependencies..."
	@which python3 > /dev/null || (echo "❌ Python 3 not found" && exit 1)
	@which node > /dev/null || (echo "❌ Node.js not found" && exit 1)
	@which npm > /dev/null || (echo "❌ npm not found" && exit 1)
	@echo "✅ System dependencies found"
	@python3 -c "import fitz" 2>/dev/null || echo "⚠️  PyMuPDF not installed (pip install pymupdf)"
	@python3 -c "import pytesseract" 2>/dev/null || echo "⚠️  pytesseract not installed (pip install pytesseract)"
	@which tesseract > /dev/null || echo "⚠️  Tesseract OCR not installed (brew install tesseract or apt install tesseract-ocr)"

# CI/CD commands
ci: lint test build
	@echo "CI pipeline completed successfully"

# Database commands
db-upgrade:
	@echo "Running database migrations..."
	@cd backend && PYTHONPATH=$$PWD alembic upgrade head

db-create:
	@echo "Creating new database migration..."
	@cd backend && PYTHONPATH=$$PWD alembic revision --autogenerate -m "$(MSG)"

# Seeding commands
seed-admin:
	@echo "Creating admin user..."
	@cd backend && PYTHONPATH=$$PWD python -m app.services.seed_users $(ARGS)

seed-categories:
	@echo "Seeding default categories..."
	@cd backend && PYTHONPATH=$$PWD python -m app.services.seed_categories

seed-all: db-upgrade seed-admin seed-categories
	@echo "Database seeded with admin user and categories"

# Development shortcuts
run-backend:
	@make dev-backend

run-frontend:
	@make dev-frontend

setup: install-backend install-frontend check-deps
	@echo "Setup completed. Run 'make dev' to start development servers."