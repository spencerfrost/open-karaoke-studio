# Unit 0 — Kill the karaoke jockey

> **Shipped 2026-08-29 as `bfffe584f`.** Kept for the reasoning; see the postscript at the
> bottom for where the implementation diverged from this plan.

Part of [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Nothing depends on this unit
landing first *for correctness*, but two later units get materially cheaper if it does.

## Context

The KJ / host dashboard was built for a bar: someone runs the night, opens and closes the
queue, caps how many songs each singer can stack, and approves submissions before they hit
the list. The actual venue is a living room with 2–5 people. The dashboard
([HostDashboard.tsx](frontend/src/pages/HostDashboard.tsx), 485 lines) has never been
used.

Deleting it is worth doing on its own, but the reason it goes **first** is that it is in the
way of two things:

- **`isHost` collapses to one meaning.** Removing `user.isHost` leaves only the device
  role, so the split stage mode needs becomes a rename — `isStageDevice` (session store)
  plus `isSessionOwner` (derived from `host_user_id`) — instead of a refactor.
- **The queue API gets clean before rotation rewrites it.** Unit 3 derives play order from a
  roster. Doing that on top of a live `pending` path means implementing the ordering
  question twice.

## The trap this closes

**The enforcement is not in the dashboard — it is in the queue API.** Deleting the frontend
alone leaves it running:

| Setting | Live effect | Only rescue |
|---|---|---|
| `queue_open: false` | 403 "Queue is currently closed" on every submission ([karaoke_queue.py:336](backend/app/api/karaoke_queue.py#L336)) | flip the row |
| `max_songs_per_singer` | 429 once a singer hits the cap ([:339-352](backend/app/api/karaoke_queue.py#L339-L352)) | flip the row |
| `queue_submission_mode: "approval"` | new items get `status="pending"` ([:375-376](backend/app/api/karaoke_queue.py#L375-L376)), which [:236](backend/app/api/karaoke_queue.py#L236) filters out of the active queue | `/approve` ([:596](backend/app/api/karaoke_queue.py#L596)) or `/reject` ([:626](backend/app/api/karaoke_queue.py#L626)) — **dashboard-only** |

So one stale `host_settings` row makes phone submissions silently disappear with nothing in
the app able to bring them back. The removal therefore has to cross the API boundary.

**It is latent, not live.** On the current DB all three KJ columns sit at defaults in every
row (`instant`, `queue_open: true`, and the admin row on `max_songs: 0`). Nothing is
stranded today, and there is no data to preserve.

## Settled decisions

| Decision | Choice |
|---|---|
| Scope | Its own change, landing **before** the session lifecycle fixes |
| Boundary | Frontend **and** backend, including the whole `pending` path |
| `sessionStore.isHost` | Split as part of this work — `isStageDevice` + `isSessionOwner` |
| `User.is_host` (account role) | **Untouched** — see below |
| `host_settings` table | **Kept**, trimmed to `session_duration_hours` |

## Two corrections found during implementation

**1. `user.isHost` is not KJ-only, and does not get dropped.** The premise this plan was
written on — "removing `user.isHost` leaves only the device role" — is wrong.
`User.is_host` gates 19 endpoints through `require_host`
([dependencies.py:72](backend/app/api/dependencies.py#L72)), including
`GET/POST /api/sessions/my`, which is exactly what `joinAsHost()` calls. Demo pool accounts
are `is_host=True, is_admin=False`, so dropping it would kill demo session auto-create. The
account role, `require_host`, `/set-host` and the AdminPanel toggle all stay.

The split is therefore entirely inside the *session* store: `isHost` → `isStageDevice`
(device role, client-decided) plus a new `isSessionOwner` (authority, server-derived). The
WS `authenticated` / `session_connected` payload field is renamed `is_host` →
`is_session_owner` to match, since that value has always been ownership
([session_specific.py:82-85](backend/app/ws/session_specific.py#L82-L85)) while the field
name invited it to be read as the device role. REST's `is_host` keeps its name — there it
really is the device.

**2. `host_settings` survives.** It becomes the per-host defaults table it was always meant
to be, holding `session_duration_hours` with room for future host-level defaults. Hosts and
admins are distinct roles and both need somewhere to set session defaults. `GET/PUT
/api/host-settings` stay, trimmed to that one field; only the three KJ columns are dropped.

## Backend

### Delete

Nothing here is deleted outright. `backend/app/api/host_settings.py` and
`backend/app/db/models/host_settings.py` are **trimmed** to `session_duration_hours`; the
router registration, the `require_host` gate and the demo 403 on PUT all stay.
`backend/scripts/manage_users.py` stops seeding the KJ fields for `--demo` accounts.

The two host-settings test files are likewise trimmed rather than deleted, and
`tests/fastapi/test_demo_login.py`'s `_seed_pool` drops the KJ kwargs while keeping its
15-minute assertion. No conftest fixture needed touching.

### Strip from the queue API — `backend/app/api/karaoke_queue.py`

- The `queue_open` rejection (`:336`) and the `max_songs_per_singer` cap (`:339-352`).
- The whole `pending` path: `item_status` selection (`:367-376`), the split at `:235-236`,
  `pending_responses` (`:265`), the `pending` field on the response model (`:105`, `:271`),
  the `broadcast_pending_update` call at `:404-405`, and the `/approve` and `/reject`
  endpoints (`:596`, `:626`).
- Every queue item is `active`, so the `status` column stops carrying meaning. Drop it — but
  note that unit 3 will add its own per-item state (`lap`), so leave the row shape alone
  otherwise.
- `backend/app/ws/queue.py:190` — `broadcast_pending_update` loses its last caller.

### Migration

One Alembic revision dropping the three KJ `host_settings` columns and `karaoke_queue.status`.
Note that autogenerate sweeps in a large amount of pre-existing SQLite→Postgres type drift, so
the generated file has to be cut back to just those four `drop_column` calls by hand. The
`downgrade()` needs `server_default`s, since all four columns are `NOT NULL`.

## Frontend

### Delete

- [pages/HostDashboard.tsx](frontend/src/pages/HostDashboard.tsx) and
  [components/HostGuard.tsx](frontend/src/components/HostGuard.tsx).
- The `/host` route and both imports in
  [App.tsx:16,21,84-90](frontend/src/App.tsx#L84-L90).
- `AdminGuard` and `/admin` **stay** — the admin panel is unrelated.

### The `isHost` split

- The auth store's `user.isHost` is **kept** (correction 1 above). Only the KJ nav item at
  [AppLayout.tsx:39](frontend/src/components/layout/AppLayout.tsx#L39) stops reading it.
- Rename the session store's `isHost` → `isStageDevice` and add `isSessionOwner`. The WS
  `authenticated` handler sets only `isSessionOwner`; it must stop overwriting the device
  flag, which is the actual conflation bug. Nearly every reader wants the device — the
  exceptions are `EndSessionButton` and `SessionStatusHeader`'s "(Host)" suffix.
- Backend: `requester_is_host` in `karaoke_queue.py` is **deleted**, not tightened — it only
  ever existed to bypass the KJ enforcement that this unit removes.

### Queue types

- [types/KaraokeQueue.ts:9](frontend/src/types/KaraokeQueue.ts#L9) — drop
  `status: "active" | "pending"`; [:25](frontend/src/types/KaraokeQueue.ts#L25) — drop
  the optional `pending` array.
- [useKaraokeQueue.ts:69,75](frontend/src/hooks/api/useKaraokeQueue.ts#L69) — drop the
  `pending` passthrough.

## Verification

**Backend**

```bash
cd backend && source venv/bin/activate
pytest                                   # full suite — this is a deletion, regressions are the risk
alembic upgrade head
```

**Frontend** — run individually, never `pnpm run check`:

```bash
cd frontend
pnpm run type-check
pnpm run lint:check
pnpm exec prettier --write "src/<only files touched>"
```

Type-check is the real safety net here: every dangling reference to `isHost`, `status`, or
`pending` surfaces as an error.

**End-to-end** — services already run under tmux and hot-reload; do not restart them.

1. `/host` 404s (or redirects), and nothing in the nav links to it.
2. Queue a song from a phone → it appears in the active queue immediately.
3. Log in as admin → `/admin` still works.
4. Confirm a session still gets a sane expiry after the `session_duration_hours` decision,
   and that a demo login still yields a 15-minute session.

```bash
tmux capture-pane -t open-karaoke:0.0 -p | tail -30   # API logs
```

---

## Postscript — what actually shipped

`bfffe584f refactor: remove the karaoke jockey and split isHost`. Three deviations from the
plan above, all deliberate:

**`host_settings` was kept, trimmed to `session_duration_hours`.** The open decision resolved
to option 2 rather than the recommended drop — the table survives as the per-host defaults
table it was always meant to be, and `demo_service.py` is untouched.

**`requester_is_host` was deleted, not tightened.** It only ever existed to bypass the
enforcement being removed here, so there was nothing left for it to gate.

**`User.is_host` stays.** It gates `require_host` on 19 endpoints including
`POST /api/sessions/my`, and demo accounts are hosts without being admins. Only the *session
store's* `isHost` was split — into `isStageDevice` (client-decided) and `isSessionOwner`
(server-derived), with the wire field renamed to match. Worth knowing: the WS `authenticated`
handler had been overwriting the device role with session ownership on every reconnect.

Also landed: `karaoke_queue.status` dropped entirely, so unit 3 adds `lap` to a clean row.
