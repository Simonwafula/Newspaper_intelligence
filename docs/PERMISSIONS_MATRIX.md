# Permissions Matrix

This document defines the role-based access control for Newspaper Intelligence.

## User Roles

- **Public**: Unauthenticated users
- **Reader**: Authenticated users with read access (formerly USER)
- **Admin**: Authenticated users with full system access

## API Endpoint Permissions

### Public Endpoints (no authentication required)
- `GET /api/public/editions` - List newspaper editions (covers only)
- `GET /api/public/editions/{id}/cover` - Get edition cover image
- `POST /api/public/access-requests` - Submit access request

### Reader Endpoints (authentication required)
- `GET /api/editions` - List editions with full details
- `GET /api/editions/{id}` - Get edition with full details
- `GET /api/editions/{id}/items` - Get items in edition (full text)
- `GET /api/items/{id}` - Get item details (full text)
- `GET /api/search` - Search within specific edition
- `GET /api/global-search` - Search across all editions
- `GET /api/saved-searches` - List saved searches
- `POST /api/saved-searches` - Create saved search
- `PUT /api/saved-searches/{id}` - Update saved search
- `DELETE /api/saved-searches/{id}` - Delete saved search
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout

### Admin-Only Endpoints (admin authentication required)
- `POST /api/editions` - Upload new edition
- `PUT /api/editions/{id}` - Update edition
- `DELETE /api/editions/{id}` - Delete edition
- `POST /api/editions/{id}/process` - Trigger processing
- `POST /api/editions/{id}/reprocess` - Re-run processing
- `POST /api/editions/{id}/archive` - Archive PDF to Drive
- `POST /api/editions/{id}/restore` - Restore archived PDF (stub)
- `GET /api/editions/{id}/processing-status` - Get processing status
- `GET /api/export/editions/{id}` - Export edition data
- `GET /api/export/search` - Export search results
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user
- `GET /api/access-requests` - List access requests
- `PUT /api/access-requests/{id}` - Approve/reject access request

## UI Component Permissions

### Public UI
- Landing page with cover gallery
- Login form
- Request access form

### Reader UI
- All public UI components
- Edition library with full item access
- Search functionality
- Saved searches
- Profile management

### Admin UI
- All Reader UI components
- Upload interface
- Export functionality
- User management
- Access request management
- Processing controls

## Data Access Rules

### Public Access
- Can view edition covers and basic metadata
- Cannot view extracted text or item details
- Cannot search or export
- Cannot access any user-specific features

### Reader Access
- Can view all edition content including full text
- Can use all search features
- Can manage saved searches
- Can read archived editions (text and cover only; no PDF)
- Cannot upload, delete, or export data
- Cannot manage users or access requests

### Admin Access
- Full access to all features
- Can upload and manage editions
- Can manually archive editions to Drive
- Can export any data
- Can manage users and access requests
- Can view processing logs and system status

## Permission Enforcement

All permissions must be enforced at both:
1. **UI Level** - Hide/disable controls based on user role
2. **API Level** - Return 401/403 for unauthorized access attempts

### Error Responses
- `401 Unauthorized` - Authentication required or invalid
- `403 Forbidden` - User authenticated but lacks required role
- `404 Not Found` - Resource not found or user lacks permission to know it exists

## Migration Notes

- Legacy `USER` role renamed to `READER` for clarity
- Admin token authentication still supported for backward compatibility
- JWT tokens now include user role in payload for role-based checks

## Implementation Status

### ✅ Completed
- User model with READER/ADMIN roles
- JWT authentication system
- Public API endpoints (editions only)
- Access request model and endpoint
- Rate limiting and bot protection

### 🔄 In Progress
- Role-based API endpoint protection
- Frontend authentication integration
- Admin user management

### ❌ TODO
- Frontend routing structure (/app/*)
- Role-based navbar components
- Admin section UI
- Comprehensive permission testing
