# Auth Hardening: Permission Ladder & Session-Member Authorization

## Context

The app is publicly hosted but was designed when every user was the owner. A security pass (already partially landed, uncommitted) added `require_host`/`require_admin`/`get_current_user` to several endpoints, but two problems remain:

1. `require_host` on `POST /api/youtube/download` broke a real party flow: anonymous session guests (joined via QR/4-char code, no account) can no longer add new songs from YouTube. They must be able to — but a *completely random API request* must not.
2. Destructive library endpoints in `songs.py` still accept **any** logged-in account (`get_current_user` only). Registration is open (`POST /users/register`, rate-limited but public), so any random registrant can delete library songs today. This gap becomes worse once performer accounts (planned) make registration a normal flow, and once demo accounts (planned, see companion plan) hand out real logins publicly.

### Target permission ladder

This is the model all auth decisions should align to (also to be documented in `docs/architecture.md`):

| Tier | Authenticated by | Can do |
|---|---|---|
| Random request | nothing | public reads only (login, register, join) |
| **Session member** (anon guest) | live server-minted `device_id` + session | browse library, queue songs, **download new songs** into their session |
| Performer (future) | account JWT | session member + favourites, own history |
| Host | account JWT, `is_host` | run sessions, playback, queue moderation |
| Admin | account JWT, `is_admin` | library maintenance, user management |

### Key insight

`POST /sessions/join-by-code` already mints an unguessable credential: `device_id = "rest_" + uuid4().hex[:12]` ([sessions.py:402](../../backend/app/api/sessions.py)), stored in `SessionDevice`. Guests already hold it (frontend `sessionStore.deviceId`). Nothing verifies it today — queue endpoints check only the guessable 4-char session code via `get_session_code` ([karaoke_queue.py:126](../../backend/app/api/karaoke_queue.py)). We verify membership instead of inventing new token machinery: one indexed DB lookup, free revocation (deactivate device / expire session), right-sized for 5–10 users.

## Changes

### 1. `require_session_member` dependency — `backend/app/api/dependencies.py`

```python
async def require_session_member(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_device_id: str = Header(..., alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> SessionDevice:
    # device exists, is_active, belongs to that session;
    # session is_active and not is_expired() → return device, else 403
```

Also a combined dependency for endpoints that accept **either** a host JWT **or** session membership (downloads). Suggested shape: `require_host_or_session_member` returning a small dataclass `RequesterContext(user: Optional[User], device: Optional[SessionDevice], session_id: Optional[str])`, so the demo-quota plan can attribute downloads to a session. Note: `HTTPBearer` raises 403 when the header is absent, so the JWT part must use an *optional* bearer scheme (`HTTPBearer(auto_error=False)`) inside this combined dependency.

### 2. Relax `download_youtube` — `backend/app/api/youtube.py`

Replace the just-added `require_host` with `require_host_or_session_member`. Anonymous guests in a live session regain new-song downloads; random requests stay 403.

### 3. Escalate destructive library endpoints to `require_admin` — `backend/app/api/songs.py`

Change `get_current_user` → `require_admin` on:
- `DELETE /songs/{song_id}` (delete_song)
- `DELETE /songs/orphan/{dir_name}`, `DELETE /songs/orphan-bulk`, `DELETE /songs/ghost-bulk`
- `POST /songs/{song_id}/reprocess`
- `POST /songs/fingerprint`, `POST /songs/backfill-artwork`, `POST /songs/backfill-duration`

Leave the read-only audit endpoints (`library-audit`, `metadata-audit`, `by-fingerprint-status`, `duplicates`) at `get_current_user` or escalate to `require_host` — decide during implementation; they leak nothing destructive. Lyrics mutation endpoints stay `get_current_user` for now (performers will legitimately edit lyrics; revisit with performer accounts).

### 4. Rate-limit session joining — `backend/app/api/sessions.py`

The 4-char display code (36⁴ ≈ 1.7M combinations) is the real gate for the anonymous tier, and `join-by-code` currently has no limiter — brute-forcing a live code is feasible. Apply the existing pattern (`from app.limiter import limiter`, as used in [users.py](../../backend/app/api/users.py)): e.g. `@limiter.limit("10/minute")` on `join-by-code` and `join-by-id`. Limiter is per-IP in-memory slowapi ([limiter.py](../../backend/app/limiter.py)) — fine at this scale.

### 5. Frontend: send `X-Device-ID` — `frontend/src/hooks/api/useApi.ts`

The auth-header helper already attaches `Authorization` when a token exists. Add `X-Session-ID` / `X-Device-ID` from `sessionStore` (both already stored there) to requests, or minimally to the download mutation path (`useYoutubeDownloadMutation` → `useSongCreation.ts` consumers). Sending both headers on all API requests is simplest and harmless.

### 6. Document the ladder — `docs/architecture.md`

Add the permission-tier table above so future endpoints (performer accounts, demo accounts) are gated consistently instead of ad hoc.

### Tests

- `require_session_member`: valid member 200; unknown device 403; device from a *different* session 403; expired session 403; missing headers 4xx.
- `download_youtube`: host JWT works; session member works; neither → 403. Existing tests pass via conftest's `get_current_user` override — the new combined dependency must remain overridable the same way (keep it resolving through `get_current_user`-compatible seams, or override the combined dependency directly in tests).
- `songs.py` escalations: non-admin user → 403 on each destructive endpoint (note shared conftest mock is admin, so add a non-admin override case).

## Verification

1. `cd backend && source venv/bin/activate && pytest`
2. Manual: create a session as host, join from an incognito window via code (no login), add a new YouTube song as the guest — download starts. Replay the same request with a fabricated `X-Device-ID` — 403.
3. As a plain registered (non-admin) user, attempt `DELETE /api/songs/{id}` — 403; as admin — works.
4. Hammer `join-by-code` with bad codes — 429 after limit.

## Out of scope

- Performer accounts (favourites, per-user history) — separate future project; this plan only keeps the ladder consistent with it.
- Demo accounts — companion plan: `2026-07-09-demo-account-pool.md` (depends on this plan landing first).
- Hardening queue endpoints to require device membership (currently session-code-only) — worthwhile follow-up using the same dependency, but not required now.
