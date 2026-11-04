# Demo API

API documentation for the public live demo: checking whether this server offers it, starting a demo session, and checking a demo session's remaining downloads.

## Base URL

```
/api/demo
```

## Overview

The live demo hands each visitor a free account from the **demo pool** (host accounts flagged `is_demo`) with its karaoke session already running. No credential is typed or published: the start endpoint issues the token itself. Pool sizing, quotas and setup are in [Demo Accounts](/demo-accounts).

Status and start need no authentication. Quota needs the session's host or a member of the session.

---

## Endpoints

### Get Demo Status

Whether this server offers the live demo. The entry page only shows **Try it live** when this is true.

```http
GET /api/demo
```

#### Response

```json
{
  "enabled": true
}
```

`enabled` is true when at least one `is_demo` account exists.

---

### Start a Demo Session

Pick a free pool account, start its session, and sign the visitor in. Rate-limited to **5 requests/hour and 12 requests/day** per IP. Every call counts, including ones that come back `503`.

```http
POST /api/demo/start
```

#### Response

The same shape as [Login](authentication.md#login). The token expires with the demo session, at the time left on it:

```json
{
  "success": true,
  "id": "7",
  "display_name": "demo-pool-1",
  "token": "jwt-token-string",
  "is_admin": false,
  "is_host": true,
  "is_demo": true
}
```

The account's session is already created when this returns, so the session clock has started. The frontend then opens the stage, whose [`POST /api/sessions/my`](sessions.md#get-or-create-my-session) reuses that session and registers the visitor's device in it. A demo account can't start or replace a session itself (see [Sessions API](sessions.md#get-or-create-my-session)), so a new session needs another call here.

#### Error Responses

- `503 Service Unavailable` — Every pool account has a live session, or there's no pool

```json
{
  "detail": "The demo is busy right now — try again in a few minutes."
}
```

- `429 Too Many Requests` — Rate limit exceeded for this IP
- `500 Internal Server Error` — The session couldn't be started

---

### Get Demo Quota

How many new songs the requester's demo session can still add. The guided tour polls this while
the visitor waits for their song, so the stage knows the downloads are used up even though the
phone is the one that got the error.

```http
GET /api/demo/quota
```

#### Response

```json
{
  "session_remaining": 2,
  "daily_remaining": 14
}
```

It uses the same counting as the limit itself: finished downloads count, and jobs created before
the current session took its code are ignored. Adding a song once either number is 0 returns
`429 Too Many Requests`.

#### Error Responses

- `403 Forbidden` — The requester isn't in a demo session

---

## Related Documentation

- [Demo Accounts](/demo-accounts) - Pool setup, quotas, and turning the demo off
- [Authentication API](authentication.md) - Login and permission tiers
- [Sessions API](sessions.md) - Session creation and joining
