# Sequencing — how stage mode, sessions, rotation and the KJ fit together

## Why this doc exists

Three plans grew in parallel and started colliding. They are not three features that
overlap; they are **one dependency chain plus two conflations in the code**. This doc
names the units, orders them, and records which plan owns each contested piece.

## The two conflations

Everything that feels tangled traces back to these:

**1. `isHost` means two different things.** *Device role* ("this browser is the TV") and
*authority* ("this user owns the session"). The WS derives the second correctly from
`host_user_id` ([session_specific.py:82-85](backend/app/ws/session_specific.py#L82-L85));
REST `/info` uses the first ([sessions.py:627](backend/app/api/sessions.py#L627));
`/leave` uses client IP; the frontend then overwrites `isHost` from the WS `authenticated`
message. Stage mode makes the *device* meaning load-bearing — it decides whether you render
a full-screen app — so the conflation gets riskier, not safer, if deferred.

**2. A singer is a string, not an entity.** The queue stores a name. Rotation needs a row
that a queue item, a lap counter, and later a user account can all point at. Every
"prompt for names more often" idea is really "give a performer an identity."

Fix those two and the plans stop competing.

## The units

> **Status 2026-09-25:** units 0–4 are shipped and their plans are in [archive/](archive/).
> Unit 3d is next. 4b and 5 are deferred.

| # | Unit | Plan | Depends on | Track |
|---|---|---|---|---|
| — | Stage redesign (3-col player) | [2026-08-28-stage-redesign.md](archive/2026-08-28-stage-redesign.md) | — | **Shipped** — `d4935f37e` |
| 0 | Kill the KJ | [2026-08-29-kj-removal.md](archive/2026-08-29-kj-removal.md) | — | **Shipped** — `bfffe584f` |
| 1 | Session lifecycle (backend) | [2026-08-29-session-lifecycle.md](archive/2026-08-29-session-lifecycle.md) | 0 | **Shipped** — `b959d6b6d` |
| 2 | Stage mode shell | [2026-08-29-stage-mode.md](archive/2026-08-29-stage-mode.md) | 1 | **Shipped** — `a1d3a2ea5` |
| 3 | Roster + derived order | [2026-08-29-roster-and-rotation.md](archive/2026-08-29-roster-and-rotation.md) | 1 | **3a shipped** — `ebf33f50f`. 3b shipped, superseded by 3d |
| 3c | Create Session screen | [2026-08-30-create-session-screen.md](archive/2026-08-30-create-session-screen.md) | 3a | **Shipped** — `cb8489d18` |
| 4 | The handoff screen | [2026-08-29-handoff-screen.md](archive/2026-08-29-handoff-screen.md) | 2 **and** 3 | **Shipped** — `d2d197206`. Turn controls superseded by 3d |
| 3d | Rotation as a circle (replaces 3b's lap model + 4's turn controls) | [2026-09-25-rotation-circle.md](2026-09-25-rotation-circle.md) | 3a, 4 | **Next.** Not started |
| 4b | Performer-seeded suggestions | [2026-08-31-performer-seeded-suggestions.md](2026-08-31-performer-seeded-suggestions.md) | 4 | Deferred |
| 5 | Performer accounts | [2026-08-29-performer-accounts.md](2026-08-29-performer-accounts.md) | 4 | Deferred |

**2 and 3 run in parallel.** That is the payoff of this ordering — after unit 1 lands there
is a frontend track and a backend track that do not touch the same files until unit 4.

**3c is a side branch off 3a, not part of the 2/3 parallel pair.** It replaces the silent
`joinAsHost()` auto-create in `Stage.tsx` with an explicit session-setup screen, and needs
only unit 3a's roster table + `resolve_or_create_performer` service to pre-seed names at
creation — it does not touch ordering (3b) or the handoff screen (4), so it can land whenever
3a is done, in parallel with either.

## Why this order

> The rotation design behind units 3–5 lives as an artifact rather than a repo file:
> [The Rotation Problem](https://claude.ai/code/artifact/e8bcfb43-9e1b-4b5d-8bbf-12d242defb6c).
> The three plan docs are the buildable version of it, reconciled against what unit 0 deleted.

**0 first, because it is deletion that unblocks two things.** Removing the KJ collapses
`isHost` to a single meaning (a rename, not a refactor) and clears the `pending` /
`queue_open` path out of the queue API *before* rotation rewrites ordering in it. It is the
cheapest unit and unblocks the most. All three KJ columns are at defaults in every row of
the live DB, so nothing is stranded and there is no data to migrate.

**Unit 0 shipped on 2026-08-29 as `bfffe584f`,** with two deviations from its plan:
`host_settings` was kept and trimmed to `session_duration_hours` rather than dropped, and
`requester_is_host` was deleted rather than tightened. `User.is_host` also stays — it gates
`require_host` on 19 endpoints. See that plan's postscript.

**1 second, because both 2 and 3 land on broken code without it.**

- Stage mode's *"Exit stage → End session"* needs an end-session endpoint. `/leave` 404s by
  construction — it looks the device up by `request.client.host`
  ([sessions.py:747](backend/app/api/sessions.py#L747)) while every REST `device_id` is
  `rest_<hex12>` — so the branch that sets `session.is_active = False` is unreachable.
- Stage mode's *"Exit stage → Keep running"* needs the session to survive the TV's socket
  dropping. Today 30s of host disconnect `db.delete`s the session
  ([session_specific.py:496](backend/app/ws/session_specific.py#L496)) and cascades the
  queue away.
- **Rotation dies on the same line.** A roster is session-scoped rows. If a locked phone
  deletes the session, it deletes the roster, the laps, and the night's order.

Session management was never a third feature. Its backend half is infrastructure for the
other two; its frontend half was absorbed by stage mode (see below).

**4 last, because it is where the two tracks meet.**

## Contested pieces, resolved

**The between-songs screen belongs to rotation, not stage mode.** Stage mode's screen table
defers *"between songs / who's up next"* as *"polish, not blocking"*; the rotation doc calls
the same screen *"the whole feature."* They are one screen. It is cut from the stage-mode
plan so no placeholder gets built and thrown away.

**Session UI belongs to stage mode, not the session plan.** The original session plan's §9
was "strip the auto-create effects, make `SessionEntry` the host's create screen." Stage
mode's answer is stronger: the desktop app should not need a session at all. Relaxing
`requireSession` on `/` and `/add` in [App.tsx:43-58](frontend/src/App.tsx#L43-L58)
leaves the auto-create paths with nothing to trigger them, so they get deleted with no
replacement screen to build. `SessionEntry` survives as the *performer* entry; `/controls`
and the join-by-code path are untouched.

**`isHost` splitting belongs to unit 0.** Both later plans deferred it and both depend on
it. Note the correction recorded in that plan: `user.isHost` (the account role) is *not*
KJ-only and survives — it gates `require_host` on 19 endpoints including
`POST /api/sessions/my`. The split is confined to the session store: `isStageDevice` (device,
client-decided) plus `isSessionOwner` (authority, from `host_user_id` over the WS).

**Logout belongs in Settings.** Its only call site today is inside `SessionEntry`'s host
card ([SessionEntry.tsx:289](frontend/src/components/SessionEntry.tsx#L289)), which
stage mode deletes. Without a new home there would be no logout anywhere in the app.

## What each unit must not do

- **0** must not touch session creation or the queue's *ordering* — only its gatekeeping.
- **1** ships no UI. It is verified by pytest and curl so the fixes stand on their own.
- **2** must not build the between-songs screen, and must not invent a session model
  beyond what unit 1 exposes.
- **3** must not touch stage-mode screens. Roster and order are backend + data model.
- **4** is the only unit allowed to assume both 2 and 3 exist.

## Open questions carried across units

- **A phone queues while the TV sits in song select.** Does the TV react and move, or stay
  put? Becomes sharper once rotation derives order. *(unit 2, settled by 3)* — **still open.**
- **Where the queue-order mode toggle lives.** Its intended home was the KJ dashboard, which
  no longer exists. Not the TV — see unit 4's "what stays off this screen." *(unit 3)* —
  **settled:** `RotationModeCard` in Settings, plus the initial choice on the Create Session screen.
- **Whether a roster entry expires**, and how long the auto-pass timer runs. *(units 3, 4)* —
  **settled:** neither. Timers and automatic removal came out in `3436292e7`; leaving is a
  deliberate "Remove from rotation" in unit 3d.
- **The permission ladder** a `Performer` tier slots into, below the surviving `User.is_host`.
  *(unit 5)*
