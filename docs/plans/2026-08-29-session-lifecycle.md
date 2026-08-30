# Unit 1 — Session lifecycle (backend)

Part of [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Depends on
[unit 0](2026-08-29-kj-removal.md). **Blocks both** [stage mode](2026-08-29-stage-mode.md)
and the rotation roster.

## Context

The original complaint was "logging in as host silently creates a session, with no UI to
manage it and no way to log out and start a new one." Tracing it found the UI was the
smaller half of the problem — **the backend end-session path cannot work**, so wiring up a
button would not have fixed anything.

### The core defect

[sessions.py:747-754](backend/app/api/sessions.py#L747) finds the device by IP:

```python
client_host = request.client.host if request.client else "unknown"
device = db.query(SessionDevice).filter(SessionDevice.device_id == client_host, ...)
```

Every `device_id` the REST API issues is `rest_<hex12>`. The filter can never match, so
`/leave` always 404s, `device.is_active = False` never runs, and the host branch that sets
`session.is_active = False` is **unreachable code**. Both callers swallow the failure
([sessionStore.ts:588](frontend/src/stores/sessionStore.ts#L588),
[EndSessionButton.tsx:29](frontend/src/features/session/components/EndSessionButton.tsx#L29)).
The session stays `is_active=True`, so `POST /api/sessions/my`
([:212](backend/app/api/sessions.py#L212)) hands the host back the same session, same
code, same queue — forever. That is exactly "can't start a new session."

### The lifecycle is backwards

Ending a session explicitly does nothing, while the host's phone locking for 30 seconds
hard-`db.delete`s the session ([session_specific.py:496](backend/app/ws/session_specific.py#L496)),
cascading to `queue_items` and `playback_state`.

### Why this is now a prerequisite, not parallel work

Stage mode's exit prompt has two branches and **both land here**: *End session* needs an
endpoint that works, and *Keep running* needs the session to survive the TV's socket
dropping. Unit 3's roster is session-scoped rows, so the same 30-second delete would take
the roster, the laps, and the night's order with it.

## Settled decisions

| Decision | Choice |
|---|---|
| Scope | **Backend only, standalone.** Verified by pytest and curl, no UI in this unit |
| WS grace expiry | Deactivate and keep the row — queue and playback state survive |
| Host on login with a live session | Auto-resume silently; only decide when none exists |
| Device leave vs. host end | Two different operations, two different endpoints |

**The frontend half moved to [unit 2](2026-08-29-stage-mode.md).** The original plan proposed
making `SessionEntry` the host's create screen; stage mode's answer is better — the desktop
app should not need a session at all, so relaxing `requireSession` on `/` and `/add` in
[App.tsx:43-58](frontend/src/App.tsx#L43-L58) leaves the auto-create paths with nothing
to trigger them. Logout lands in Settings. Both are unit 2's work, not this one's.

## 1 · Separate "device leaves" from "host ends session"

`backend/app/api/sessions.py`

- **`POST /{session_id}/leave`** — resolve the device from the request instead of the IP.
  Reuse the existing authorization primitive `require_session_member`
  ([dependencies.py:119](backend/app/api/dependencies.py#L119)), which validates
  `X-Session-ID` + `X-Device-ID` against a live session and 403s otherwise. Verify the
  resolved device's `session_id` matches the path param. Drop the host-ends-session branch
  entirely — it moves to DELETE.
- **New `DELETE /{session_id}`** — `require_host` plus an ownership check
  (`session.host_user_id == current_user.id`; 403 otherwise, so one host cannot end
  another's session). Set `session.is_active = False`, deactivate every `SessionDevice` row,
  and close the sockets via `request.app.state.session_manager`
  ([main.py:107](backend/app/main.py#L107)) calling the existing
  `force_close_session_connections(session_id, reason=...)`
  ([connection_manager.py:202](backend/app/ws/connection_manager.py#L202)) — it already
  broadcasts `session_ended` and force-closes the room. **Keep the session row, queue items,
  and playback state.**

## 2 · Grace expiry deactivates, not deletes

[session_specific.py:496](backend/app/ws/session_specific.py#L496) currently
`db.delete(session)`. Replace with `session.is_active = False` plus device deactivation, so a
host whose phone locked can reopen and resume. Keep the existing `session_ended` broadcast
and socket teardown around it.

This is the line stage mode's *"Keep running"* branch depends on, and the line that would
otherwise eat unit 3's roster.

## 3 · Keep the code space healthy now that rows survive

`session_id` doubles as the 4-char `display_code` and is UNIQUE
([session.py:26-27](backend/app/db/models/session.py#L26)), so retained rows permanently
retire codes. Add `purge_stale_sessions(db, older_than_days=...)` next to the existing
`deactivate_expired_sessions` ([sessions.py:128](backend/app/api/sessions.py#L128)) and
call both at the top of `POST /api/sessions/my`. `generate_display_code` and its
`IntegrityError` retry loop need no change.

## 4 · Make `POST /api/sessions/my` idempotent per device

It inserts a new `SessionDevice` unconditionally
([sessions.py:248](backend/app/api/sessions.py#L248)), so every mount inflates
`device_count` and the connected-devices list. Add optional `device_id` to
`SessionCreateRequest`; when supplied and an active device with that id already belongs to
the session, reuse it instead of inserting.

## 5 · Derive host identity from `host_user_id`

`GET /{session_id}/info` ([sessions.py:627](backend/app/api/sessions.py#L627)) computes
`is_host` from `device_id == host_device_id`. Prefer an optional bearer token compared
against `host_user_id`, falling back to the device comparison for anonymous callers.

> The `requester_is_host` tightening in `karaoke_queue.py` and the frontend
> `isStageDevice` / `isSessionOwner` rename land in [unit 0](2026-08-29-kj-removal.md). If
> unit 0 has not shipped, do them here instead — do not do them twice.

## 6 · Tests — new `backend/tests/fastapi/test_sessions.py`

There is currently **no REST coverage for sessions** (only WS-level tests). Follow the
fixtures in `backend/tests/fastapi/conftest.py`.

- `/leave` deactivates the correct device row — regression for the IP bug
- `DELETE` requires host, 403s for a non-owning host, deactivates session + devices, and
  leaves queue rows intact
- `POST /my` returns the same session on a second call, and does not add a second device row
  when `device_id` is passed
- **`POST /my` after `DELETE` yields a new session with a different code** — the acceptance
  test for the original complaint
- WS grace expiry deactivates rather than deletes, and the queue survives

## Verification

```bash
cd backend && source venv/bin/activate
pytest tests/fastapi/test_sessions.py -v
pytest                                   # full suite for regressions
```

Manual, via curl — services already run under tmux and hot-reload; do not restart them:

1. `POST /api/sessions/my` twice with the same `device_id` → same session, `device_count`
   unchanged.
2. `POST /{id}/leave` with valid `X-Session-ID` / `X-Device-ID` headers → 200, that device
   row is inactive, session still active.
3. `DELETE /{id}` as the owning host → 200; session `is_active=False`; queue rows still
   present in the DB.
4. `DELETE /{id}` as a different host account → 403.
5. `POST /api/sessions/my` again → **new session, different code.**
6. Connect the host WS, drop it for >30s → session row survives with `is_active=False` and
   its queue intact.

```bash
tmux capture-pane -t open-karaoke:0.0 -p | tail -30   # API logs
```
