# Create Session screen

Sibling to [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Depends on
[unit 3a — roster](2026-08-29-roster-and-rotation.md) for the "pre-list performer names"
field; the session-settings half has no dependency and could ship alone if 3a slips.

## Why

Today, walking into the stage is silent. `Stage.tsx`'s bootstrap effect
([Stage.tsx:77-97](frontend/src/pages/Stage.tsx#L77)) tries `recoverSession()` and, if that
finds nothing live, immediately calls `joinAsHost()`
([sessionStore.ts:127](frontend/src/stores/sessionStore.ts#L127)) — an idempotent
get-or-create hit against `POST /api/sessions/my`. There's no moment where the host is asked
anything; the TV just appears with an empty queue and a 4-letter code. That's the "unceremonious"
gap: starting a karaoke night has no beginning, the way opening a world in a game does.

The fix is a screen in that exact seam — not a new route, not a new guard. `requireSession` on
`/stage` already stays `false` ([App.tsx:73](frontend/src/App.tsx#L73)); this only changes what
`Stage.tsx` renders while `displayCode` is still null and no recovery candidate exists.

## What it replaces, precisely

`initializeSession()`'s current branch:
```ts
const state = useSessionStore.getState();
if (!state.displayCode) {
  await joinAsHost();
}
```
becomes: render `<CreateSessionScreen onStart={...} />` instead of calling `joinAsHost()`
automatically. `onStart` collects the form values and calls a new store action (see below)
that performs the same `POST /api/sessions/my`, now carrying the setup payload.

**Unit 1's "auto-resume silently; only decide when none exists" is preserved as-is** — if
`recoverSession()` finds a live session, this screen never renders; the decision point is
identical to today's, just with a screen sitting in the branch that used to be silent.

## Screen content (Minecraft "Create New World" framing, scaled to this app)

- **Session length** — pre-filled from `HostSettings.session_duration_hours`
  ([host_settings.py:22](backend/app/db/models/host_settings.py#L22), today's default of 8h,
  read server-side at [sessions.py:360-362](backend/app/api/sessions.py#L360)), editable as a
  one-off override for tonight only. Does **not** change the host's stored default — this is
  "how long is tonight," not a settings-page edit.
- **Who's coming tonight?** — a free-text add/remove name list, entirely optional/skippable.
  This is the fourth roster entry point the roster doc didn't anticipate: the host pre-seeds
  the roster before anyone has joined or queued anything, so the stage picker's name grid
  (`SongConfirmScreen`, per unit 3a) isn't empty for the first song of the night.
- **Start Session** — the only required action. Skipping the name list is the common case for
  a two-person living-room session; it must not feel mandatory.

## Backend

Extend `SessionCreateRequest` ([sessions.py:69](backend/app/api/sessions.py#L69)) with two
optional fields:
```python
duration_hours: Optional[float] = Field(None, description="Override tonight's session length")
performer_names: Optional[List[str]] = Field(None, description="Pre-seed the roster")
```
In `get_or_create_my_session` ([sessions.py:256](backend/app/api/sessions.py#L256)):
- Use `session_data.duration_hours or duration_hours` (the existing `HostSettings` lookup)
  when calling `KaraokeSession.create_new_session(...)` — override, don't replace, the
  existing default-lookup logic at [:360-371](backend/app/api/sessions.py#L360).
- After the session is committed, loop `performer_names` through unit 3a's
  `resolve_or_create_performer(db, session.session_id, name)`
  (`backend/app/services/roster_service.py`) — the same function every other entry point
  calls, so a pre-seeded name behaves identically to one added later (dedupes by normalized
  name, gets a seat, etc).
- Both fields are optional and additive — this endpoint's existing no-payload call
  (`joinAsHost`'s current behavior, and every other caller of `POST /my`) is unaffected.

No new endpoint. No migration — this reuses unit 3a's table and service as-is.

## Frontend

- New `frontend/src/features/stage/screens/CreateSessionScreen.tsx` (or a top-level component
  if `Stage.tsx` renders it before `StageShell` mounts — it appears *before* there is a
  session, so it lives outside `StageShell`/`StageShellContext`, unlike the other stage
  screens which all assume a live session and queue).
- `sessionStore.ts`: extend `joinAsHost` (or add a sibling `createSessionWithSetup(options)`
  that calls the same idempotent `POST /my`) to accept `{ durationHours?, performerNames? }`
  and thread them into the request body next to the existing `device_type` /
  `device_id`.
- `Stage.tsx`'s `isConnecting` "Creating Session..." loading branch
  ([Stage.tsx:164-183](frontend/src/pages/Stage.tsx#L164)) stays exactly as-is — it now
  covers the moment between tapping "Start Session" and the response, not the whole silent
  auto-create.

## What this explicitly does not do

- Does not touch the `queue_order_mode` / rotation toggle — that's unit 3b/4's territory and
  the sequencing doc already says it must not live on the TV
  ([2026-08-29-sequencing.md](2026-08-29-sequencing.md), "Open questions carried across
  units").
- Does not change recovery behavior, `/leave`, or `DELETE /{session_id}` — this is purely the
  creation path.
- Does not require performer accounts (unit 5) — pre-seeded names are anonymous roster rows,
  identical to a walk-up who never picks up a phone.

## Sequencing

Slot into [2026-08-29-sequencing.md](2026-08-29-sequencing.md)'s unit table as **unit 3c**,
depending on unit 3a, parallel to unit 3b and unit 4 (neither of which it touches).

## Verification

**Backend**
```bash
cd backend && source venv/bin/activate
pytest tests/fastapi/test_sessions.py -v   # extend: duration_hours override, performer_names pre-seed
```
1. `POST /api/sessions/my` with `performer_names: ["Dan", "Sarah"]` → two `session_performers`
   rows exist for the new session, seats 0 and 1.
2. `POST /api/sessions/my` with `duration_hours: 2` → `expires_at` reflects the override, not
   the host's stored default.
3. `POST /api/sessions/my` with no body (today's exact call) → unchanged behavior.

**Frontend**
```bash
cd frontend && pnpm run type-check && pnpm run lint:check
```
**End-to-end** (tmux services already running):
1. Log in as host with no live session, hit `/stage` → the create screen appears instead of
   an empty queue.
2. Add two names, start → both appear in the roster (`GET /api/sessions/{id}/performers`) and
   in the stage picker's grid on the very first song.
3. Skip the name list entirely → session starts with an empty roster, exactly like today.
4. Reload `/stage` mid-session → recovery finds the live session, the create screen does not
   reappear.
