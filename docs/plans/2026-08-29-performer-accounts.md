# Unit 5 — Performer accounts

Part of [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Depends on
[unit 3](2026-08-29-roster-and-rotation.md) for the roster and
[unit 4](2026-08-29-handoff-screen.md) for the surfaces that benefit.

**Deferred by design.** This unit is written down now so that unit 3 adds two nullable
columns in its migration instead of needing a second one later. Nothing here has to be built
for units 3 and 4 to ship.

Design source: [The Rotation Problem](https://claude.ai/code/artifact/e8bcfb43-9e1b-4b5d-8bbf-12d242defb6c),
section 07.

## Context

Optional performer accounts land on the roster cleanly **because the roster was specified as
name-bound rather than device-bound**. An account becomes a third optional binding on the same
anchor, not a competing identity.

The codebase already has this pattern one level up: `KaraokeSession.host_user_id` is a
nullable FK to `users` on a session-scoped row, and `User` already carries `display_name`,
`is_host`, `is_admin`, `is_demo`. A roster entry does the same thing one level down.

**The rotation math does not change at all.** `seat`, `laps_taken` and `lap` all live on the
roster entry. Accounts never touch the sort, the handoff screen, or the pass-forward.

## Settled decisions

| Decision | Choice |
|---|---|
| Binding | A third optional binding on the roster entry — never a replacement identity |
| Columns | Added in unit 3's migration, unread until this unit |
| Login mid-session | **Links to the existing entry, never creates a second one** |
| Queue items | `KaraokeQueueItem.performer_id` points at the roster, **never** at `users` |
| The invariant | Accounts grant conveniences, never capabilities |

## Two nullable columns, added in unit 3

- **`SessionPerformer.user_id`** — nullable FK to `users`. Costs nothing while unused, saves
  a migration later.
- **`PerformanceHistory.user_id`** — nullable, **denormalized at write time** alongside
  `performer_id`. This is the non-obvious one: sessions expire and roster rows get cleaned up
  (unit 1's `purge_stale_sessions`), so lifetime history cannot hang off a session-scoped join
  or it dangles.

Keep `KaraokeQueueItem.performer_id` pointed at the roster. **The moment a queue item requires
an account, walk-up singers stop existing** — which is the entire population unit 3 exists to
include.

## Logging in mid-session links, never creates

Sarah joins anonymously, sings three songs, then logs in. Attach the account to her
**existing** roster entry and backfill `user_id` on this session's history rows — she keeps
her seat, her lap counter, and her place in the circle. Creating a second entry would silently
cost her a turn.

The reverse collision is the one to plan for: Sarah logs in on her phone *and* someone already
added "Sarah" at the stage picker. Two entries, one person. Normalized-name matching
(`lower(trim(name))`, already unit 3's rule) catches most of it; the rest wants a host-side
merge — repoint queue items and history, sum `laps_taken`, keep the lower seat. Small feature,
but it exists.

## The rule that keeps accounts optional

**Accounts grant conveniences, never capabilities.** Claiming a turn, passing yourself, and
picking a song must all work fully anonymously, or the design collapses back into the thing it
replaced. This is easy to violate by accident once a `Performer` tier exists in the permission
ladder, which is why it is written down rather than left implied.

What accounts genuinely improve — all of it on unit 4's slowest moment, the empty slot:

- **Suggestions get good.** The performer-seeded tiles go from "songs by the artist who just
  played" to "songs you haven't sung yet" — the
  [useSongSuggestions](frontend/src/features/player/hooks/useSongSuggestions.ts) doc comment's own
  stated goal, finally backed by lifetime history.
- **Favourites** become the fast path for the pick-a-song moment.
- **Rejoining is frictionless** — recognized on arrival, seat restored.

## Two tradeoffs to accept on purpose

**An account-linked roster entry can still be claimed by whoever is standing at the TV.**
*That's not me* cannot demand a login without ruining it. For a living room that is correct —
the threat model is your friends. Worth accepting explicitly rather than discovering it.

**Identity remains weak, and that is now fully accepted.** The original note here was that
accounts *harden* `max_songs_per_singer` without fixing it, since an anonymous walk-up can
retype a slightly different name for a fresh allowance. [Unit 0](2026-08-29-kj-removal.md)
deleted that cap outright, so there is nothing left to harden — but the underlying point
stands for anything built later: **do not add a per-person limit that assumes a strong
identity.** The demo-account pool means `user_id` does not imply "trusted" either.

## Prerequisite before building this

`User.is_host` survived unit 0 — it gates `require_host` on 19 endpoints including
`POST /api/sessions/my`, and demo accounts are hosts without being admins. A `Performer` tier
must slot in **below** that without widening what `is_host` means. Settle the permission
ladder before writing any of this, or the "conveniences, never capabilities" rule gets
violated in the first endpoint.

## Verification

Deferred with the unit. When it is built, the acceptance tests that matter:

1. Sarah joins anonymously, queues songs, then logs in → **one** roster entry, seat and
   `laps_taken` preserved, this session's history backfilled with her `user_id`.
2. Sarah logs in on her phone while "Sarah" already exists from the stage picker → the two
   entries are matched, or a host-side merge is offered. Never two people.
3. A fully anonymous walk-up can claim a turn, pass themselves, and pick a song — every path
   works with no account at all.
4. A roster row is purged with its session; the corresponding `performance_history` rows
   survive with a readable `user_id` and singer name.
