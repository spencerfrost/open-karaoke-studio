# Authentication API

API documentation for user management and authentication endpoints.

## Base URL

```
/api/users
```

## Overview

Open Karaoke Studio uses a lightweight account system (username + password, JWT tokens) combined with anonymous session membership. Most guest actions don't need an account — guests join a karaoke session with a 4-character code and are authorized as **session members**. Accounts exist for **hosts** (run sessions, moderate the queue) and **admins** (library maintenance, user management).

### Permission ladder

Gate every endpoint against one of these tiers, never ad hoc.

| Tier | Authenticated by | Can do |
|---|---|---|
| Anyone | nothing | Log in, register, join or validate a session, start the demo, load media (covers, thumbnails, artist images, track files, YouTube previews) |
| **Session member** (a guest's phone) | `X-Session-ID` + `X-Device-ID`, minted by joining | Browse the library, add songs to the library and to *their* session's queue, use the roster and turn controls at the handoff screen, report lyrics |
| Account | JWT, no flags | Browse the library and add songs to it. Not any session's queue: a session needs its member device, its host or an admin |
| Host | JWT, `is_host` | Start and run their own sessions: playback, queue moderation, ending the night, the recap playlist |
| Admin | JWT, `is_admin` | Everything a host can, in any session, plus library maintenance, jobs, lyrics reports and user management |

The rules live in `backend/app/api/dependencies.py`: `require_host_or_session_member` accepts
either credential (keeping both when both are sent), and `ensure_session_access` narrows that to
one session. The join endpoints are rate limited per IP, since the 4-letter code is the gate for
the anonymous tier. [Platform Foundations § Who gets in](/domains/platform-foundations#who-gets-in-two-layers-of-gate)
has the full dependency ladder and the frontend's matching gates.

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
  "is_host": true,
  "is_demo": false
}
```

`is_demo` is true for a [demo pool](/demo-accounts) account. Visitors don't log in to the demo with a username: [`POST /api/demo/start`](demo.md#start-a-demo-session) hands them a free pool account and returns this same response.

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
| Random request | nothing | login, register, join session, the demo start, and the media URLs (thumbnails, covers, artist images, track files) |
| Session member (anon guest) | `X-Session-ID` + `X-Device-ID` headers from session join | browse library, queue songs, download new songs in their session |
| Any account | JWT | browse library, edit lyrics; *not* another session's queue or roster |
| Host | JWT with `is_host` | run their own sessions, playback control, queue moderation, their own performance history |
| Admin | JWT with `is_admin` | every session, jobs, lyrics reports, library maintenance, user management |

**An account is not a session membership.** Registration and the [demo](demo.md) hand out
accounts to anyone, so session-scoped endpoints (queue, roster, session info, playlist) admit only a
member device of that session, the account that hosts it, or an admin. Someone else's session and a
code that doesn't exist both return `403`, so these endpoints can't be used to find live codes. The
same rule is why the endpoints that span every session (jobs, lyrics reports, library audits) are
admin-only rather than host-only.

**An expired token doesn't lock out a guest.** When a request carries a bad token *and* a valid
session credential, it proceeds as that session's guest. With no session credential to fall back on,
the bad token is a `401`.

**Third-party proxies are rate limited per client IP**: YouTube search and preview, YouTube Music
browse, lyrics provider search, and lyrics alignment. See [Client IPs behind the proxy](/guide#client-ips-behind-the-proxy).

---

## Token Details

- **Format:** JWT, sent as `Authorization: Bearer {token}`
- **Passwords:** hashed with bcrypt
- **Demo accounts:** `POST /api/demo/start` issues host-permission tokens that expire with the demo session (see [Demo API](demo.md) and [Demo Accounts](/demo-accounts))
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
- [Platform Foundations](/domains/platform-foundations) - How the gates are wired, frontend and backend
- [Roadmap](/roadmap) - Planned auth features
