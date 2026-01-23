# Permissions Matrix - Newspaper PDF Intelligence

## Current Implementation Analysis

### Authentication State
- **User Model**: ❌ **NOT IMPLEMENTED** - No User model with roles exists
- **Authentication**: ❌ **NOT IMPLEMENTED** - No login/logout, JWT, or session system
- **Authorization**: ⚠️ **PARTIAL** - Only admin token protection for write operations

### Current API Surface

| Endpoint Group | Public | Reader | Admin | Current Status | Issues |
|---|---|---|---|---|---|
| **Editions** |
| GET /api/editions (list) | ❌ | ✅ | ✅ | Admin token NOT required | Should be public for covers only |
| GET /api/editions/{id} (detail) | ❌ | ✅ | ✅ | Admin token NOT required | No public endpoint exists |
| POST /api/editions (upload) | ❌ | ❌ | ✅ | Admin token REQUIRED | ✅ Correct |
| DELETE /api/editions/{id} | ❌ | ❌ | ✅ | Admin token REQUIRED | ✅ Correct |
| POST /api/editions/{id}/reprocess | ❌ | ❌ | ✅ | Admin token REQUIRED | ✅ Correct |
| **Items** |
| GET /api/items/edition/{id}/items | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| GET /api/items/item/{id} | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| **Search** |
| GET /api/search/edition/{id}/search | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| GET /api/search/search (global) | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| **Export** |
| GET /api/export/edition/{id}/export/{item_type}.csv | ❌ | ❌ | ✅ | Admin token NOT required | ❌ **MAJOR SECURITY ISSUE** |
| GET /api/export/edition/{id}/export/all.csv | ❌ | ❌ | ✅ | Admin token NOT required | ❌ **MAJOR SECURITY ISSUE** |
| **Saved Searches** |
| GET /api/saved-searches | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| POST /api/saved-searches | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| PATCH/DELETE saved searches | ❌ | ✅ | ✅ | Admin token NOT required | Should require authentication |
| **Public Endpoints (REQUIRED)** |
| GET /api/public/editions (covers) | ❌ | ✅ | ✅ | **NOT IMPLEMENTED** | ❌ **MISSING** |
| GET /api/public/editions/{id}/cover | ❌ | ✅ | ✅ | **NOT IMPLEMENTED** | ❌ **MISSING** |

## Critical Issues

### 🚨 **SECURITY VIOLATIONS**
1. **Export endpoints are publicly accessible** - Anyone can download all extracted data without authentication
2. **No user authentication system** - Cannot distinguish between public, reader, and admin access
3. **All data is publicly readable** - No protection for story text, classifieds details, or search functionality

### 🚨 **JTBD COMPLIANCE GAPS**
1. **Public users can see everything** - Violates "Public MUST NOT see any extracted story text, classifieds details"
2. **No public cover-only view** - Missing required public API surface
3. **No role-based access control** - Cannot enforce Reader vs Admin permissions

## Required Implementation

### 1. User Authentication System
```python
# New model needed
class User(Base):
    id: int
    email: str (unique)
    password_hash: str
    role: str (READER, ADMIN)
    is_active: bool
    created_at: datetime
    last_login: datetime
```

### 2. Authentication Dependencies
```python
# New auth dependencies needed
async def get_current_user(...)
async def get_current_reader(...)  # READER or ADMIN
async def verify_public_access(...)  # No auth required
```

### 3. Public API Endpoints
```python
# New router needed: /api/public/
GET /api/public/editions  # Covers + metadata only
GET /api/public/editions/{id}/cover  # Cover image only
```

### 4. Protected API Endpoints
All current endpoints (except health check) need to be protected:
- Reader-level: GET endpoints for items, search, saved searches
- Admin-level: All write operations, export endpoints

## Implementation Priority

### Phase 1: Critical Security (IMMEDIATE)
1. Protect export endpoints with admin token **RIGHT NOW**
2. Implement User model and basic authentication
3. Add JWT/session management
4. Create public endpoints

### Phase 2: Role Enforcement (HIGH)
1. Migrate all GET endpoints to require reader authentication
2. Implement proper role-based dependencies
3. Update frontend to handle authentication

### Phase 3: Testing & Validation (HIGH)
1. Create comprehensive test suite for permissions
2. Test all endpoint combinations
3. Verify JTBD compliance

## Security Requirements

### Password Security
- Minimum 8 characters
- Hash with bcrypt or Argon2
- Rate limiting on login attempts

### Token Security
- JWT with expiration (15 minutes access, 7 days refresh)
- OR server-side sessions with secure cookies
- CSRF protection for cookies

### API Security
- Rate limiting per user
- Input validation and sanitization
- HTTPS only in production

## Testing Requirements

### Required Test Cases
1. **Public Access Test**: Anonymous users can only access public endpoints
2. **Export Security Test**: Export endpoints return 401/403 without auth
3. **Reader Access Test**: Readers can read but not export or upload
4. **Admin Access Test**: Admins can perform all operations
5. **Role Escalation Test**: Users cannot access higher privilege functions

### Test Commands
```bash
# Test public access
curl -X GET "http://localhost:8007/api/public/editions"  # Should work
curl -X GET "http://localhost:8007/api/editions"  # Should fail (401)

# Test export security
curl -X GET "http://localhost:8007/api/export/edition/1/export/all.csv"  # Should fail (401)

# Test admin token
curl -H "X-Admin-Token: secret" -X GET "http://localhost:8007/api/export/edition/1/export/all.csv"  # Should work
```

## Frontend Changes Required

### Authentication UI
- Login page
- Logout functionality  
- Session management
- Role-based UI rendering

### API Integration
- All API calls must include auth headers
- Handle 401/403 responses
- Public vs authenticated content separation

## Deployment Considerations

### Environment Variables
```bash
# New required variables
SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Database Migration
- Add User table
- Create initial admin user
- Update existing data if needed

### Security Headers
- Strict-Transport-Security
- X-Content-Type-Options
- X-Frame-Options
- Content-Security-Policy