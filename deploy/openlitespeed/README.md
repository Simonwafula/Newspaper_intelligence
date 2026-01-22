# Security Configuration Guide

## Overview

This guide explains how to secure the Newspaper Intelligence application for production deployment using OpenLiteSpeed and Basic Authentication.

## Security Features

### 1. Admin Token Protection

All write operations (POST, PUT, DELETE) are protected by an `ADMIN_TOKEN` environment variable.

#### Configuration

Set the `ADMIN_TOKEN` environment variable in your production environment:

```bash
# Generate a secure token (use openssl or a password manager)
export ADMIN_TOKEN="your-secure-random-token-here"
```

#### Implementation

- Frontend sends the token in `X-Admin-Token` header
- Backend validates token on all write operations
- Read operations (GET) remain publicly accessible
- Token is never logged or exposed in error messages

### 2. OpenLiteSpeed Basic Authentication

Additional layer of protection using HTTP Basic Auth for the entire application.

#### Configuration

1. Access your OpenLiteSpeed WebAdmin console
2. Navigate to: `Virtual Hosts > your-vhost > Context > /`
3. Add the following configuration:

```xml
<context>
    <realm>Protected Area</realm>
    <user>
        <name>admin</name>
        <password>your-secure-password</password>
        <group>admin</group>
    </user>
    <auth>
        <type>Basic</type>
        <name>Protected Area</name>
    </auth>
</context>
```

#### Using .htpasswd (Alternative)

Create a password file:

```bash
# Install htpasswd generator if needed
sudo apt install apache2-utils

# Create password file
sudo htpasswd -c /etc/litespeed/.htpasswd admin
# You'll be prompted to enter a secure password

# Set proper permissions
sudo chmod 640 /etc/litespeed/.htpasswd
sudo chown www-data:www-data /etc/litespeed/.htpasswd
```

Then configure in OpenLiteSpeed:

```xml
<auth>
    <type>Basic</type>
    <name>Newspaper Intelligence</name>
    <userdb>
        <type>File</type>
        <location>/etc/litespeed/.htpasswd</location>
    </userdb>
</auth>
```

### 3. Storage Security

Ensure uploaded PDFs and generated images are not directly accessible.

#### Directory Structure

```
/var/www/newspaper-intelligence/
├── public/          # Web accessible
│   ├── index.html
│   └── static/
└── storage/         # NOT web accessible
    ├── editions/
    └── processing/
```

#### OpenLiteSpeed Configuration

1. In your Virtual Host configuration, deny access to the storage directory:

```xml
<context>
    <type>static</type>
    <uri>/storage/</uri>
    <location>/var/www/newspaper-intelligence/storage</location>
    <accessControl>
        <deny>*</deny>
    </accessControl>
</context>
```

2. Alternatively, place storage outside the web root:

```xml
# Better: Place storage outside web root
/storage/    # /var/lib/newspaper-intelligence/storage
public/      # /var/www/newspaper-intelligence/public
```

### 4. HTTPS/TLS Configuration

#### SSL Certificate Setup

1. Obtain SSL certificate (Let's Encrypt recommended):

```bash
# Install certbot
sudo apt install certbot python3-certbot-apache

# Get certificate
sudo certbot --apache -d your-domain.com
```

2. Configure OpenLiteSpeed to use SSL:

```xml
<listener>
    <name>SSL</name>
    <address>*:443</address>
    <secure>1</secure>
    <keyFile>/etc/letsencrypt/live/your-domain.com/privkey.pem</keyFile>
    <certFile>/etc/letsencrypt/live/your-domain.com/fullchain.pem</certFile>
</listener>
```

3. Force HTTPS redirect:

```xml
<rewrite>
    <enable>1</enable>
    <rules>
        <rule>
            <matchType>HTTP</matchType>
            <matchValue>off</matchValue>
            <actionType>Redirect</actionType>
            <actionValue>https://%{HTTP_HOST}%{REQUEST_URI}</actionValue>
        </rule>
    </rules>
</rewrite>
```

## Environment Variables

### Required for Production

```bash
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost/newspaper_db

# Security
ADMIN_TOKEN=your-secure-random-token-here

# Storage
STORAGE_PATH=/var/lib/newspaper-intelligence/storage

# Production settings
DEBUG=false
LOG_LEVEL=INFO
```

### Optional but Recommended

```bash
# CORS (restrict to your frontend domain)
ALLOWED_ORIGINS=https://your-domain.com

# Rate limiting (if implemented)
RATE_LIMIT_PER_MINUTE=60

# File size limits
MAX_PDF_SIZE=50MB
```

## Frontend Configuration

Update your frontend `.env.production` file:

```env
VITE_API_URL=https://your-domain.com/api
VITE_ADMIN_TOKEN=your-secure-random-token-here
```

## Security Headers

Configure OpenLiteSpeed to add security headers:

```xml
<context>
    <extraHeaders>
        <add>Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'</add>
        <add>X-Frame-Options: DENY</add>
        <add>X-Content-Type-Options: nosniff</add>
        <add>X-XSS-Protection: 1; mode=block</add>
        <add>Referrer-Policy: strict-origin-when-cross-origin</add>
        <add>Permissions-Policy: camera=(), microphone=(), geolocation=()</add>
    </extraHeaders>
</context>
```

## Monitoring and Logging

### Application Logs

Configure logging to monitor security events:

```python
# In backend/app/settings.py
LOG_LEVEL=INFO  # or WARNING for production
```

### Access Logs

OpenLiteSpeed access logs show:
- Failed authentication attempts
- Blocked requests
- Suspicious patterns

Monitor these logs regularly:

```bash
tail -f /usr/local/lsws/logs/access.log
```

### Security Alerts

Set up alerts for:
- Multiple failed authentication attempts
- Unexpected admin token usage
- Access to blocked directories

## Backup and Recovery

### Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/var/backups/newspaper-intelligence"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump newspaper_db > "$BACKUP_DIR/db_$DATE.sql"

# Keep only last 30 days
find "$BACKUP_DIR" -name "db_*.sql" -mtime +30 -delete
```

### Storage Backups

```bash
# Backup uploaded files
rsync -av /var/lib/newspaper-intelligence/storage/ \
  /var/backups/newspaper-intelligence/storage_$(date +%Y%m%d)/
```

## Security Checklist

- [ ] ADMIN_TOKEN set and properly secured
- [ ] OpenLiteSpeed Basic Auth configured
- [ ] Storage directory not web accessible
- [ ] HTTPS/TLS configured with valid certificate
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] File upload size limits configured
- [ ] Logging and monitoring in place
- [ ] Backup procedures established
- [ ] Regular security updates applied
- [ ] Password strength requirements enforced
- [ ] Access logs reviewed regularly

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check ADMIN_TOKEN is correctly set in frontend and backend
2. **403 Forbidden**: Verify OpenLiteSpeed auth configuration
3. **Storage files accessible**: Check directory permissions and OpenLiteSpeed context rules
4. **CORS errors**: Verify ALLOWED_ORIGINS configuration

### Testing Security

```bash
# Test admin token protection
curl -X POST http://localhost:8007/api/editions \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  # Should return 401

curl -X POST http://localhost:8007/api/editions \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secure-token" \
  -d '{"test": "data"}' \
  # Should work with valid token

# Test storage protection
curl -I http://your-domain.com/storage/editions/some-file.pdf
# Should return 403
```

## Contact and Support

For security-related issues:
- Check application logs first
- Review OpenLiteSpeed configuration
- Verify environment variables
- Monitor access patterns for suspicious activity