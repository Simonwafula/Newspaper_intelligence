# Deployment Context — mag.mstatilitechnologies.com

This file is the single source of truth for deployment facts. Do not change these values without updating this document.

## Domain & Panel
- **Subdomain:** `mag.mstatilitechnologies.com`
- **Panel:** CyberPanel
- **Web server:** OpenLiteSpeed (OLS)
- **Process supervisor:** systemd
- **Reverse proxy:** OpenLiteSpeed → FastAPI backend on localhost

## Linux Account & Paths
- **Linux user/group:** `magms2596`
- **Git/project root (web root):**
  - `/home/mag.mstatilitechnologies.com/public_html/`
  - This is where we `git pull` from GitHub.
- **Python venv location (outside web root):**
  - `/home/mag.mstatilitechnologies.com/.venv`
- **Environment file (outside web root):**
  - `/home/mag.mstatilitechnologies.com/.env`
- **Storage directory (outside web root):**
  - `/home/mag.mstatilitechnologies.com/storage`
- **Logs directory (outside web root):**
  - `/home/mag.mstatilitechnologies.com/logs`

Recommended final layout:
/home/mag.mstatilitechnologies.com/
.env
.venv/
storage/
logs/
public_html/
backend/
frontend/
deploy/
agent-work.md


## Database Strategy
- **Development default:** SQLite
- **Production:** PostgreSQL
- Use `DATABASE_URL` to switch:
  - Dev example: `DATABASE_URL=sqlite:///./dev.db`
  - Prod example: `DATABASE_URL=postgresql+psycopg://USER:PASS@127.0.0.1:5432/mag_news`

## Required Directories & Permissions
Create:
- `/home/mag.mstatilitechnologies.com/storage`
- `/home/mag.mstatilitechnologies.com/logs`

Ownership:
- `magms2596:magms2596` should own these directories.

## Backend Service (systemd)
Backend runs as:
- `uvicorn app.main:app --host 127.0.0.1 --port 8000`

Expectations:
- Only listens on localhost (not public)
- OpenLiteSpeed proxies public traffic to it
- Logs go to `/home/mag.mstatilitechnologies.com/logs/`

Service file template must live in repo:
- `deploy/systemd/mag-newspaper-api.service`

## OpenLiteSpeed Reverse Proxy
OpenLiteSpeed (CyberPanel vhost) must be configured to proxy:
- `/` (and `/api`) → `http://127.0.0.1:8000`

Because no Docker is used, backend must always be reachable locally.

If serving frontend statically:
- Build React app (`frontend/dist`) and configure OLS docroot to serve it.
- API requests go to `/api/...` on same domain.

## Access Control (Required)
This subdomain is public. Add protection.

### Primary protection (recommended)
- Enable **HTTP Basic Auth** in OpenLiteSpeed using:
  - Realm + `htpasswd` file

Implementation note:
- The `htpasswd` file must be readable by the OpenLiteSpeed user (commonly `lsadm`).
- Keep `htpasswd` outside public_html.

Repo must include documentation:
- `deploy/openlitespeed/README.md` with step-by-step CyberPanel/OLS instructions.

### App-level protection (optional but recommended)
- Support `ADMIN_TOKEN` (env var) and require it for write endpoints:
  - upload
  - delete edition
  - reprocess edition

## Environment Variables (Production)
Store in `/home/mag.mstatilitechnologies.com/.env`:

Minimum:
- `DATABASE_URL=postgresql+psycopg://...`
- `STORAGE_PATH=/home/mag.mstatilitechnologies.com/storage`
- `LOG_PATH=/home/mag.mstatilitechnologies.com/logs`
- `DEBUG=false`

OCR:
- `OCR_ENABLED=true`
- `OCR_LANGUAGES=eng`

Processing knobs:
- `MIN_CHARS_FOR_NATIVE_TEXT=200`
- `MAX_PDF_SIZE_MB=50`

Security:
- `ADMIN_TOKEN=...` (optional)

## Deployment Routine
The deploy script must:
1) `git pull` in `/home/mag.mstatilitechnologies.com/public_html/`
2) ensure venv exists in `/home/mag.mstatilitechnologies.com/.venv`
3) install backend requirements
4) run Alembic migrations with prod DATABASE_URL
5) build frontend
6) restart systemd service

Script must live in repo:
- `scripts/deploy.sh`

## Notes
- No Docker.
- Do not place `.env` or `.venv` inside `public_html`.
- Do not expose storage directory directly via the web server.
- Always prefer safe file-serving endpoints controlled by the backend.
