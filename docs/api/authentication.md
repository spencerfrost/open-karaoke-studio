# Authentication API

API documentation for user management and authentication endpoints.

## Base URL

```
/api/users
```

## Overview

Open Karaoke Studio uses a lightweight account system (username + password, JWT tokens) combined with anonymous session membership. Most guest actions don't need an account — guests join a karaoke session with a 4-character code and are authorized as **session members**. Accounts exist for **hosts** (run sessions, moderate the queue) and **admins** (library maintenance, user management).

See [Architecture: Permission Ladder](/architecture#authorization-permission-ladder) for how the tiers fit together.

### Authorization headers

```
Authorization: Bearer {token}   # Account-gated endpoints (host/admin)
X-Session-ID: {session_id}      # Session membership (anonymous guests)
X-Device-ID: {device_id}        # Session membership credential minted at join
```

---

## Endpoints

### Register User

Create a new user account. Rate-limited to **3 requests/minute** per IP.

```http
POST /api/users/register
```

#### Request Body

```json
{
  "username": "johndoe",
  "password": "securePassword123",
  "display_name": "John Doe"
}
```

`username` and `password` (min 8 characters) are required; `display_name` is optional.

#### Response (`201 Created`)

```json
{
  "success": true,
  "id": "1"
}
```

#### Error Responses

- `400 Bad Request` — Username already exists
- `429 Too Many Requests` — Rate limit exceeded

---

### Login

Authenticate a user and receive a JWT token. Rate-limited to **5 requests/minute** per IP.

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
  "success": true,
  "id": "1",
  "display_name": "John Doe",
  "token": "jwt-token-string",
  "is_admin": false,
  "is_host": true
}
```

Demo-account usernames resolve through the [demo account pool](/demo-accounts) and receive short-lived host tokens.

#### Error Responses

- `401 Unauthorized` — Invalid username or password
- `429 Too Many Requests` — Rate limit exceeded

---

### Update User

Update display name and/or password. **Requires authentication.** Users can only update their own account unless they are an admin. Demo accounts cannot be modified.

```http
PATCH /api/users/{user_id}
```

#### Request Body

At least one field is required:

```json
{
  "display_name": "John Smith",
  "password": "newPassword123"
}
```

#### Response

```json
{
  "success": true
}
```

#### Error Responses

- `400 Bad Request` — No fields provided
- `403 Forbidden` — Not your account (and not admin), or demo account
- `404 Not Found` — User doesn't exist

---

### List Users

List all users. **Admin only.**

```http
GET /api/users
```

#### Response

```json
[
  {
    "id": 1,
    "username": "johndoe",
    "display_name": "John Doe",
    "is_admin": false,
    "is_host": true
  }
]
```

---

### Set Host Flag

Toggle the `is_host` flag on a user. **Admin only.**

```http
POST /api/users/{user_id}/set-host?is_host=true
```

#### Response

```json
{
  "success": true
}
```

---

## Permission Tiers

| Tier | Authenticated by | Can do |
|---|---|---|
| Random request | nothing | public reads only (login, register, join session) |
| Session member (anon guest) | `X-Session-ID` + `X-Device-ID` headers from session join | browse library, queue songs, download new songs in their session |
| Host | JWT with `is_host` | run sessions, playback control, queue moderation, job management |
| Admin | JWT with `is_admin` | library maintenance, user management |

---

## Token Details

- **Format:** JWT, sent as `Authorization: Bearer {token}`
- **Passwords:** hashed with bcrypt
- **Demo accounts:** short-lived tokens with host permissions (see [Demo Accounts](/demo-accounts))
- Anonymous guests never receive JWTs — their credential is the server-minted `device_id` from [session join](sessions.md)

---

## Usage Examples

```bash
# Register new user
curl -X POST http://localhost:5123/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "securePassword123", "display_name": "John Doe"}'

# Login
curl -X POST http://localhost:5123/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "securePassword123"}'

# Update display name
curl -X PATCH http://localhost:5123/api/users/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"display_name": "John Smith"}'

# Admin: list users
curl http://localhost:5123/api/users -H "Authorization: Bearer {admin-token}"

# Admin: grant host permission
curl -X POST "http://localhost:5123/api/users/2/set-host?is_host=true" \
  -H "Authorization: Bearer {admin-token}"
```

---

## Related Documentation

- [Sessions API](sessions.md) - Session creation and anonymous membership
- [Demo Accounts](/demo-accounts) - The demo account pool
- [Architecture: Permission Ladder](/architecture#authorization-permission-ladder) - Authorization design
- [Roadmap](/roadmap) - Planned auth features
