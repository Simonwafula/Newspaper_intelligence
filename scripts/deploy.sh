#!/bin/bash

# Newspaper Intelligence - Deployment Script
# Deploy the application to production VPS
# Usage: ./scripts/deploy.sh

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER="magms2596"
PROJECT_ROOT="/home/mag.mstatilitechnologies.com"
PUBLIC_HTML="${PROJECT_ROOT}/public_html"
VENV_PATH="${PROJECT_ROOT}/.venv"
ENV_FILE="${PROJECT_ROOT}/.env"
STORAGE_PATH="${PROJECT_ROOT}/storage"
LOGS_PATH="${PROJECT_ROOT}/logs"
SERVICE_NAME="mag-newspaper-api"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if running as correct user
# check_user() {
#     if [[ "$(whoami)" != "$DEPLOY_USER" ]]; then
#         error "This script must be run as user: $DEPLOY_USER"
#         error "Current user: $(whoami)"
#         error "Run: su - $DEPLOY_USER"
#         exit 1
#     fi
#     success "Running as correct user: $DEPLOY_USER"
# }

# Create required directories
create_directories() {
    log "Creating required directories..."
    
    mkdir -p "$STORAGE_PATH"
    mkdir -p "$LOGS_PATH"
    
    # Set correct ownership
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$STORAGE_PATH"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$LOGS_PATH"
    
    # Set correct permissions
    chmod 755 "$STORAGE_PATH"
    chmod 755 "$LOGS_PATH"
    
    success "Directories created and permissions set"
}

# Update code from git
update_code() {
    log "Updating code from git repository..."
    
    cd "$PUBLIC_HTML"
    
    # Check if we're in a git repository
    if [[ ! -d ".git" ]]; then
        error "Not in a git repository. Please clone the repository first."
        exit 1
    fi
    
    # Stash any local changes (optional - comment out if you want to fail instead)
    if ! git diff --quiet || ! git diff --cached --quiet; then
        warning "Local changes detected. Stashing them..."
        git stash push -m "Auto-stash before deploy $(date)"
    fi
    
    # Pull latest changes
    git pull origin main
    
    success "Code updated successfully"
}

# Setup or update Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    if [[ ! -d "$VENV_PATH" ]]; then
        log "Creating new virtual environment..."
        python3 -m venv "$VENV_PATH"
    else
        log "Virtual environment already exists"
    fi
    
    # Activate virtual environment and install dependencies
    source "$VENV_PATH/bin/activate"
    cd "$PUBLIC_HTML/backend"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    success "Virtual environment setup completed"
}

# Check environment file
check_env_file() {
    log "Checking environment configuration..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Environment file not found: $ENV_FILE"
        error "Please create the environment file with required variables:"
        error "  DATABASE_URL, STORAGE_PATH, LOG_PATH, DEBUG=false"
        exit 1
    fi
    
    # Load environment file to validate
    source "$ENV_FILE"
    
    # Check required variables
    local required_vars=("DATABASE_URL" "STORAGE_PATH" "LOG_PATH")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
    
    success "Environment file validation passed"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    source "$VENV_PATH/bin/activate"
    source "$ENV_FILE"
    
    cd "$PUBLIC_HTML/backend"
    export PYTHONPATH="$PUBLIC_HTML"
    
    # Run migrations
    alembic upgrade head
    
    success "Database migrations completed"
}

# Build frontend
build_frontend() {
    log "Building frontend for production..."
    
    cd "$PUBLIC_HTML/frontend"
    
    # Install dependencies
    npm install
    
    # Build for production
    npm run build
    
    success "Frontend build completed"
}

# Setup and restart systemd service
setup_service() {
    log "Setting up systemd service..."
    
    # Copy service file to systemd directory (requires sudo)
    local service_file="/etc/systemd/system/${SERVICE_NAME}.service"
    local template_file="$PUBLIC_HTML/deploy/systemd/${SERVICE_NAME}.service"
    
    if [[ ! -f "$template_file" ]]; then
        error "Service template not found: $template_file"
        exit 1
    fi
    
    # Check if we can copy the service file
    if [[ -w "/etc/systemd/system/" ]]; then
        cp "$template_file" "$service_file"
        systemctl daemon-reload
        success "Service file installed and systemd reloaded"
    else
        warning "Cannot install service file (requires sudo)"
        warning "Please run: sudo cp \"$template_file\" \"$service_file\""
        warning "Then run: sudo systemctl daemon-reload"
    fi
    
    # Restart the service
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Restarting existing service..."
        systemctl restart "$SERVICE_NAME"
    else
        log "Starting new service..."
        systemctl start "$SERVICE_NAME"
    fi
    
    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME"
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Service is running successfully"
        systemctl status "$SERVICE_NAME" --no-pager -l
    else
        error "Service failed to start"
        systemctl status "$SERVICE_NAME" --no-pager -l
        exit 1
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait a moment for service to fully start
    sleep 5
    
    # Check if backend is responding
    if curl -f -s "http://127.0.0.1:8007/api/healthz" > /dev/null; then
        success "Backend health check passed"
    else
        error "Backend health check failed"
        error "Check logs at: $LOGS_PATH/api-error.log"
        exit 1
    fi
}

# Cleanup old logs (optional)
cleanup_logs() {
    log "Cleaning up old logs (keeping last 7 days)..."
    
    find "$LOGS_PATH" -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    success "Log cleanup completed"
}

# Main deployment function
main() {
    log "Starting Newspaper Intelligence deployment..."
    log "Deploying to: $PROJECT_ROOT"
    
    #check_user
    create_directories
    update_code
    setup_venv
    check_env_file
    run_migrations
    build_frontend
    setup_service
    health_check
    cleanup_logs
    
    success "🚀 Deployment completed successfully!"
    success ""
    success "Application URLs:"
    success "  - Frontend: https://mag.mstatilitechnologies.com"
    success "  - API: https://mag.mstatilitechnologies.com/api"
    success "  - API Docs: https://mag.mstatilitechnologies.com/docs"
    success ""
    success "Service Management:"
    success "  - Status: systemctl status $SERVICE_NAME"
    success "  - Logs: journalctl -u $SERVICE_NAME -f"
    success "  - Restart: systemctl restart $SERVICE_NAME"
}

# Handle script interruption
trap 'error "Deployment interrupted"; exit 130' INT

# Run main function
main "$@"