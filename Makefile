.PHONY: help dev dev-frontend lint test clean install-backend install-frontend

help:
	@echo "Available commands:"
	@echo "  install-backend   - Install Python dependencies"
	@echo "  install-frontend   - Install Node.js dependencies"
	@echo "  dev               - Start backend development server"
	@echo "  dev-frontend      - Start frontend development server"
	@echo "  lint              - Run backend linting"
	@echo "  test              - Run backend tests"
	@echo "  clean             - Clean temporary files"

install-backend:
	cd backend && python -m venv .venv
	cd backend && source .venv/bin/activate && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

lint:
	cd backend && source .venv/bin/activate && ruff check .
	cd backend && source .venv/bin/activate && ruff format .

test:
	cd backend && source .venv/bin/activate && pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	cd frontend && rm -rf dist node_modules/.cache