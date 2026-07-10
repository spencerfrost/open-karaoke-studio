# Public Demo Account Pool for Portfolio Use

**Depends on:** `2026-07-09-auth-hardening-session-members.md` (permission ladder, `require_host_or_session_member` on downloads, `require_admin` on destructive endpoints). Do not start this until that plan has landed — demo accounts are real logins, and without the hardening they could delete library songs.

## Context

The app is a portfolio piece, but hosting a session requires an account with `is_host=True`, grantable only by an admin — so visitors (recruiters, other devs) can't try the standout flow: search YouTube Music, download a song, get AI-separated vocals/instrumental, run a karaoke session. Goal: one published username/password on the portfolio site that lets a visitor genuinely host a session, without exposing the homelab to unbounded compute and without two simultaneous visitors colliding into each other's session.

Constraints discovered during design:

- Sessions are **per-account**, not per-login: `get_or_create_my_session` ([sessions.py:169](../../backend/app/api/sessions.py)) reuses any active session for the same `host_user_id` across all devices. One shared demo account ⇒ simultaneous visitors share one session. Hence a **pool** of demo accounts behind one published alias.
- Separation compute is already globally capped: the audio Celery worker runs `--concurrency=1` (`backend/run_celery.sh`). The abuse risk is job *volume* over time, so the guard is a download quota, not concurrency control.
- Queuing an existing library song ([karaoke_queue.py:291](../../backend/app/api/karaoke_queue.py) `add_to_queue`) never touches Celery — it stays unlimited. Only `POST /api/youtube/download` costs compute.
- Anonymous guests of a demo session can also trigger downloads (by design, per the hardening plan), so the quota must be keyed to the **session**, not just the JWT user.
- `HostSettings.session_duration_hours` is an `Integer` ([host_settings.py:23](../../backend/app/db/models/host_settings.py)); 15-minute demo sessions need finer granularity.

## Design decisions (settled with Spencer)

- One published alias (e.g. `demo` / rotating password) resolved server-side to a free pool account — visitors never see the pool.
- Pool of 3 accounts; all occupied ⇒ friendly "demo is busy, try again in a few minutes" error.
- Quotas: **3 downloads per demo session**, **20/day shared across the whole pool** (sized so ~10 visitors doing 1–2 songs each fits, but leaked credentials can't run up unbounded compute).
- Demo sessions expire after **15 minutes**.

## Changes

### 1. Migration (alembic)

- `users.is_demo` — Boolean, non-null, server default false.
- `jobs.session_id` — nullable String FK-ish reference to the karaoke session that initiated the job (used for quota counting; also generally useful attribution). Optionally `jobs.user_id` (nullable) for host-initiated attribution while we're in there.
- `host_settings.session_duration_hours` — Integer → Float (SQLite and Postgres both tolerate this; `timedelta(hours=0.25)` works fine downstream in `KaraokeSession.create_new_session`).

Update the corresponding models: [user.py](../../backend/app/db/models/user.py), [job.py](../../backend/app/db/models/job.py), [host_settings.py](../../backend/app/db/models/host_settings.py).

### 2. Seed the pool — `backend/scripts/manage_users.py`

The `create` command currently only supports `--admin` (`is_host` is never settable from the CLI). Add `--host` and `--demo` flags. Seed `demo-pool-1..3` with `is_host=True`, `is_demo=True`, unguessable individual passwords (never published; the alias is the public credential), plus a `HostSettings` row each: `session_duration_hours=0.25`, `queue_submission_mode="instant"`, `max_songs_per_singer=5`.

### 3. Alias login — `backend/app/api/users.py` / `backend/app/services/auth_service.py`

In `login_user`: if submitted credentials match env-configured `DEMO_LOGIN_USERNAME` / `DEMO_LOGIN_PASSWORD` (add to `backend/app/config/base.py`; feature disabled when unset), select a pool account (`is_demo=True`) having **no active, unexpired session** (same query shape as [sessions.py:184-190](../../backend/app/api/sessions.py)) and issue that account's JWT via the existing `create_access_token`. All pool accounts busy ⇒ 503 with a friendly "demo is busy" message the login form will surface. Normal (non-alias) logins are untouched; the pool accounts' real passwords still work individually (useful for testing).

No frontend changes required — the existing login form works as-is. Optional nicety: show the 503 message verbatim.

### 4. Session/job attribution — `backend/app/api/youtube.py`, `backend/app/services/youtube_service.py`

`download_youtube` already receives requester context from `require_host_or_session_member` (hardening plan). Thread the resolved `session_id` (member's session, or the host's active session) and `user_id` (if JWT) into `YouTubeService.download_and_process_async` → stored on the `Job` row.

### 5. Quota enforcement — in `download_youtube`, before dispatching

Resolve the relevant session's `host_user_id`; if that user `is_demo`:

1. **Per-session cap:** count `Job` rows with this `session_id` — ≥ 3 ⇒ 429 "Demo limit: 3 new songs per session. You can still queue anything already in the library."
2. **Shared daily cap:** count `Job` rows joined to sessions whose host is any `is_demo` user with `created_at > now-24h` — ≥ 20 ⇒ 429 "The demo's daily download budget is used up — existing library songs still work."

Non-demo hosts/sessions: zero behavior change, no counting.

### 6. Portfolio copy (outside this repo)

Publish the alias credentials + a one-liner: "Sessions last 15 min, 3 new song downloads per session — everything else is the real app."

## Not doing

- No demo-mode UI banners/watermarks — it's the real app, that's the point. (Could add a small "demo session" chip later.)
- No periodic cleanup task for expired sessions — they lazily invalidate via `is_expired()`; 15-min sessions keep clutter minor.
- No CAPTCHA / IP throttling on the alias — the quotas already bound worst-case cost; revisit only if abused.

## Verification

1. Migration up/down cleanly; `manage_users.py create --host --demo` seeds pool + HostSettings.
2. Log in with the alias → JWT for a free pool account; session expires_at ≈ now+15min.
3. Second concurrent alias login (incognito) → *different* pool account, separate session. Fourth concurrent login (pool exhausted) → friendly 503.
4. In a demo session: 3 downloads succeed, 4th → 429 with the friendly message; queuing existing library songs still works after the cap.
5. Insert/backdate `Job` rows to exceed the 20/day pool cap → any demo session's download → 429; a real (non-demo) host's download is unaffected.
6. Anonymous guest joined to a *demo* session via code: their downloads count against the same session cap (no bypass).
7. Let a demo session idle past 15 min → next alias login reuses that freed account.
8. `pytest` green; real-user login/download flows byte-for-byte unchanged when `DEMO_LOGIN_USERNAME` is unset.
