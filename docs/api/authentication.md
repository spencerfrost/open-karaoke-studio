# Authentication API

API documentation for user management and authentication endpoints.

## Base URL

```
/api/users
```

## Overview

The Users API provides basic user management functionality. **Note:** This authentication system is minimal and primarily serves as a placeholder for future development. The application currently functions without authentication for local/family use.

> **⚠️ Current Status:** Authentication is **optional** and not enforced by default. See [Roadmap](../ROADMAP.md) for planned authentication improvements.

---

## Endpoints

### Register User

Create a new user account.

```http
POST /api/users/register
```

#### Request Body

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securePassword123",
  "display_name": "John Doe"
}
```

#### Response

```json
{
  "id": "user-uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "display_name": "John Doe",
  "created_at": "2026-01-28T10:00:00Z",
  "message": "User registered successfully"
}
```

#### Error Responses

**409 Conflict - User already exists:**
```json
{
  "error": "Username or email already exists",
  "code": "USER_EXISTS"
}
```

**400 Bad Request - Validation error:**
```json
{
  "error": "Invalid email format",
  "code": "VALIDATION_ERROR",
  "details": {
    "field": "email"
  }
}
```

---

### Login

Authenticate a user and receive session token.

```http
POST /api/users/login
```

#### Request Body

```json
{
  "username": "johndoe",
  "password": "securePassword123"
}
```

#### Response

```json
{
  "token": "jwt-token-string",
  "user": {
    "id": "user-uuid",
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe"
  },
  "expires_at": "2026-01-29T10:00:00Z"
}
```

#### Error Responses

**401 Unauthorized - Invalid credentials:**
```json
{
  "error": "Invalid username or password",
  "code": "INVALID_CREDENTIALS"
}
```

---

### Update Profile

Update user profile information.

```http
PATCH /api/users/{user_id}
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `user_id` | string | User UUID   |

#### Request Body

All fields are optional:

```json
{
  "display_name": "John Smith",
  "email": "newemail@example.com",
  "password": "newPassword123"
}
```

#### Response

```json
{
  "id": "user-uuid",
  "username": "johndoe",
  "email": "newemail@example.com",
  "display_name": "John Smith",
  "updated_at": "2026-01-28T11:00:00Z",
  "message": "Profile updated successfully"
}
```

---

## Authentication Flow

### Current Implementation (Minimal)

```
1. User registers → POST /api/users/register
2. User logs in → POST /api/users/login
3. Receives JWT token
4. Not currently required for API access
```

### Planned Improvements

Future authentication enhancements will include:
- **Required authentication** for all endpoints
- **Session persistence** across devices
- **Role-based access control** (host, performer, viewer)
- **OAuth integration** (Google, GitHub, etc.)
- **Password reset** functionality
- **Email verification**

See [Roadmap: User Accounts](../ROADMAP.md#user-accounts) for details.

---

## User Model

### Database Schema

| Field         | Type     | Description                    |
|--------------|----------|--------------------------------|
| `id`         | string   | UUID primary key               |
| `username`   | string   | Unique username                |
| `email`      | string   | Unique email address           |
| `password`   | string   | Hashed password (bcrypt)       |
| `display_name`| string  | User's display name            |
| `created_at` | datetime | Registration timestamp         |
| `updated_at` | datetime | Last update timestamp          |
| `is_active`  | boolean  | Account active status          |

---

## Password Requirements

Current password requirements (minimal):
- Minimum 8 characters
- No complexity requirements

**Planned Improvements:**
- Minimum 12 characters
- Require uppercase, lowercase, number, special char
- Password strength meter
- Common password blacklist

---

## Session Management

### Current State

- JWT tokens issued on login
- 24-hour expiration (default)
- No refresh tokens
- Session not tied to karaoke sessions

### Planned Improvements

- Refresh token support
- Configurable token expiration
- Device-specific sessions
- Session revocation
- "Remember me" functionality

---

## Error Codes

| Error Code            | HTTP Status | Description                    |
|----------------------|-------------|--------------------------------|
| `USER_EXISTS`        | 409         | Username/email already taken   |
| `INVALID_CREDENTIALS`| 401         | Wrong username or password     |
| `USER_NOT_FOUND`     | 404         | User doesn't exist             |
| `VALIDATION_ERROR`   | 400         | Invalid input data             |
| `UNAUTHORIZED`       | 401         | Authentication required        |
| `FORBIDDEN`          | 403         | Insufficient permissions       |

---

## Usage Examples

### Registration and Login

```bash
# Register new user
curl -X POST http://localhost:5123/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securePassword123",
    "display_name": "John Doe"
  }'

# Login
curl -X POST http://localhost:5123/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securePassword123"
  }'
```

### Update Profile

```bash
# Update display name
curl -X PATCH http://localhost:5123/api/users/user-uuid \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "display_name": "John Smith"
  }'
```

### JavaScript Integration

```javascript
// Register user
async function registerUser(userData) {
  const response = await fetch('http://localhost:5123/api/users/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }
  
  return await response.json();
}

// Login user
async function loginUser(username, password) {
  const response = await fetch('http://localhost:5123/api/users/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });
  
  if (!response.ok) {
    throw new Error('Invalid credentials');
  }
  
  const data = await response.json();
  
  // Store token
  localStorage.setItem('authToken', data.token);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  return data;
}

// Make authenticated request
async function makeAuthenticatedRequest(url, options = {}) {
  const token = localStorage.getItem('authToken');
  
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
}
```

---

## Security Considerations

### Current Implementation

- **Password Hashing:** bcrypt with default salt rounds
- **Token Format:** JWT (JSON Web Token)
- **Token Storage:** Client-side (localStorage)
- **HTTPS:** Not enforced (development only)

### Security Limitations

> **⚠️ Important:** The current authentication system is **not production-ready**. It lacks many security features expected in a production environment.

**Missing Security Features:**
- No HTTPS enforcement
- No CSRF protection
- No rate limiting on login attempts
- No account lockout after failed attempts
- No two-factor authentication
- No session invalidation on logout
- Token stored in localStorage (XSS vulnerable)

### Recommendations for Production

1. **Enable HTTPS** - Use TLS certificates
2. **Add Rate Limiting** - Prevent brute force attacks
3. **Implement CSRF Protection** - Use CSRF tokens
4. **Use HTTP-only Cookies** - Store tokens securely
5. **Add 2FA Support** - Multi-factor authentication
6. **Session Management** - Proper logout/revocation
7. **Security Headers** - CSP, HSTS, etc.

---

## Use Cases

### Current Use Cases

The minimal authentication system serves these purposes:

1. **User Preferences:**
   - Save default singer name
   - Remember favorite songs
   - Store playback preferences

2. **Session History:**
   - Track which songs user has sung
   - View past karaoke sessions
   - Personal statistics

3. **Basic Access Control:**
   - Distinguish between session host and performers
   - Track who added which songs to queue

### Future Use Cases

Planned authentication features will enable:

- **Multi-user Households** - Separate preferences per user
- **Guest Access** - Limited access for guests
- **Parental Controls** - Content filtering
- **Usage Analytics** - Per-user statistics
- **Social Features** - Friend lists, sharing

---

## Migration Path

For users running without authentication:

1. **Optional Migration:**
   - Authentication remains optional
   - Existing sessions continue to work
   - No breaking changes

2. **Enabling Authentication:**
   - Set `REQUIRE_AUTH=true` in environment
   - Existing data migrated to anonymous user
   - Users prompted to create accounts

3. **Future Default:**
   - Authentication may become default in v3.0
   - Clear migration guide provided
   - Backward compatibility maintained

---

## Related Documentation

- [Sessions API](sessions.md) - Session management without authentication
- [Roadmap: User Accounts](../ROADMAP.md#user-accounts) - Planned authentication features
- [Tech Debt: Authentication](../TECH-DEBT.md) - Known authentication limitations
- [Contributing: Security](../contributing.md) - Security contribution guidelines

---

## Notes

- **Personal Use:** The app is designed for small family/friend gatherings, not as a public service
- **Authentication Optional:** Works perfectly fine without user accounts for local use
- **Future Enhancements:** Authentication will be fully implemented if/when needed for multi-user scenarios
- **Community Feedback:** User authentication requirements driven by community needs
