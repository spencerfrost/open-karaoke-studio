# Rotation as a circle, not a lap count

Supersedes the ordering half of [unit 3 — roster + rotation](archive/2026-08-29-roster-and-rotation.md)
(Stage 3b) and the turn controls of [unit 4 — the handoff screen](archive/2026-08-29-handoff-screen.md).
The roster itself (Stage 3a) stands: `SessionPerformer`, name matching, and
`resolve_or_create_performer` are unchanged. Append mode is unchanged.

## Context

After the first live night, the handoff timers and automatic roster removal came out
(`3436292e7`). Looking at the whole system afterwards showed that the timers had been hiding
a problem with the model itself, not just rough edges.

The shipped design is **song-first**. Each queue item carries an immutable `lap`, and the
rotation of *people* is reconstructed from those items, with three counters holding it together:
`performer.laps_taken`, `session.current_lap`, and `performer.first_queued_at` as the
tie-break inside a lap. The turn is derived by comparing a person's "due lap" against the
head item's lap.

How the night actually runs is **person-first**:

- If you're part of the night, you're in the rotation. There is no roster-vs-rotation split.
- When it's your turn and nothing is queued, you walk up to the TV, hit Browse Library, pick
  a song and sing it. That's the normal case, not an edge case.
- Order within a lap doesn't matter. It just has to be a stable circle.

Every operation the night needs is awkward in the lap model:

| Need | Lap model |
|---|---|
| Walk-up with nothing queued | "Empty seat" rule comparing two independently maintained counters |
| Skip my turn | Rewrite `lap` on each of their items **and** `laps_taken` |
| Insert someone at the TV, right now, keeping that spot | No real mechanism. The in-lap order is a timestamp, so we'd have to forge one |
| Remove from the night, with undo | Snapshot and restore several counters |
| Bump without shifting everyone else | `advance_to` sets `current_lap = max(current_lap, item.lap)` and moves the room forward |

Two bugs found in review are the same kind of problem: separate numbers that have to agree
and drift apart.

- **Skip causes back-to-back songs.** `pass_turn` moves only the head item forward one
  lap. If Sarah has songs in laps 2 and 3, both end up in lap 3 and play consecutively.
- **Playing out of order jumps the room forward.** Playing a lap-3 item while the room is on
  lap 1 sets `current_lap = 3`. Everyone with nothing queued loses their lap-1 and lap-2
  turns, and anything queued afterwards lands at lap 3 or later.

## The model: a circle, a pointer, and personal song lists

```
   circle (seat order, fixed for the night)

        ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
   ┌──▶ │ Spencer  │ ──▶ │   Dan    │ ──▶ │ Patrick  │ ──▶ │  Sarah   │ ──┐
   │    │ seat 0   │     │ seat 1   │     │ seat 2   │     │ seat 3   │   │
   │    └──────────┘     └──────────┘     └──────────┘     └──────────┘   │
   │                                           ▲                          │
   │                                        pointer                       │
   └──────────────────────────────────────────────────────────────────────┘
                                   (lap wraps here)

   each person's own songs, oldest first
     Spencer  [Song A, Song B]
     Dan      [Song C]
     Patrick  [ ]              ← his turn: he walks up and picks at the TV
     Sarah    [Song D]
```

- **The circle** is the active performers ordered by `seat`. One lap is one pass from the
  lowest seat to the highest.
- **The pointer** (`session.turn_performer_id`) is whose turn is next. It's stored, not
  derived: it is the only source of truth for the turn, so nothing else can disagree with it.
- **Each person's songs** are their own queue items, ordered by `id`. The next song is the
  first song of whoever the pointer is on.

### Everything the night needs, in this model

| Action | What happens |
|---|---|
| **Walk-up** | The pointer is on someone with an empty list. The screen names them and waits |
| **A song starts** (`/play`) | If it's the pointer person's song, the pointer moves to the next active seat |
| **Skip my turn** | The pointer moves to the next active seat. Their songs don't move, so each one is now a lap later |
| **Add performer** (TV) | New seat inserted *at* the pointer. They're up now, and whoever was up goes next. They keep that seat for the night |
| **Join by phone / any other path** | New seat appended after the highest seat, which is the end of the current lap |
| **Remove from rotation** | `is_active = false`. The pointer moves on if it was on them. Their songs are hidden, not deleted |
| **Undo remove** | `is_active = true`, same seat, and the pointer goes back to them |
| **Bump / play out of order** | Their song plays now **as their next turn** (the borrowed turn, model A). `turns_borrowed += 1`. The pointer skips them once when it next reaches them |

Worked through:

```
   Before: pointer on Patrick (nothing queued)

   Skip           Spencer  Dan  Patrick  [Sarah]    ← pointer moves on, Patrick's list untouched

   Add "Jess"     Spencer  Dan  [Jess]  Patrick  Sarah
                                   ▲ inserted at the pointer; Patrick is next, then Sarah

   Remove         Spencer  Dan  ░Patrick░  [Sarah]  ← hidden, not deleted; undo restores seat + pointer

   Dan's song     Spencer  Dan¹ [Patrick]  Sarah    ← Dan sings now; ¹ = pointer steps over him
   played early                                        once on the next lap. Patrick is still up after
```

### What the upcoming list shows

In rotation mode, `get_ordered_queue_items` becomes a **projection**. Starting at the pointer,
walk the circle lap by lap, taking each person's *k*-th song on the *k*-th pass, stepping over
borrowed turns, and skipping people who have run out of songs. It's a pure function of the
circle, the pointer, `turns_borrowed` and the items, and at 5–10 people it costs nothing.

The walk-up case is not in the song list, because there's no song. It shows in `turn` (kind
`empty_seat`) and in the ribbon, which is `turn.circle` starting from the pointer.

## Decisions

| Decision | Choice |
|---|---|
| Roster vs rotation | **Same thing.** Every active performer is in the circle, whether or not they've queued anything |
| Order within a lap | `seat`. Whoever is seated first goes first. Nobody cares, as long as it's stable |
| Skip | Pointer moves on. **Every** one of their songs effectively moves back one lap. Never deactivates them |
| "That's not me" | **Removed.** The rotation is authoritative; nobody overrules it from the TV |
| Add performer from the TV | Inserted **at the pointer**. They sing now, the displaced person is next |
| Joining any other way | Appended to the end of the circle, which is the end of the current lap |
| Keeping a spot | A seat is fixed from the moment you join, for the whole night |
| Leaving the night | "Remove from rotation" on the handoff screen, with an undo toast. No confirm dialog |
| Removed person's songs | **Hidden, not deleted.** Undo is then just a flag flip, and someone who comes back later has their songs back. Host can still delete songs individually |
| Out of order / bump | **Borrowed turn (model A).** The song counts as their next turn; nobody else moves |
| Room lap counter | **Gone.** Nothing can jump the room forward, because nothing counts laps |

## Schema

One migration.

**Add**
- `karaoke_sessions.turn_performer_id`: nullable FK → `session_performers.id`,
  `ondelete=SET NULL`. Null means "start at the lowest active seat", which covers new
  sessions, sessions created before this migration, and a pointer whose performer row has
  gone.
- `karaoke_sessions.bumped_item_id`: nullable FK → `karaoke_queue.id`, `ondelete=SET NULL`.
  A one-off "this song is next" set by Bump. It takes precedence over the pointer for one
  turn and is cleared when that song starts. This is what lets Bump work *during* a song,
  when `/play` isn't happening yet.
- `session_performers.turns_borrowed`: int, default 0.

**Drop**
- `karaoke_queue.lap`
- `karaoke_sessions.current_lap`
- `session_performers.laps_taken`
- `session_performers.first_queued_at`

**Reinterpret**
- `session_performers.seat` changes from "join order, display only" to "place in the circle".
  Same column, same values for existing rows. Seats are renumbered on insert: every row with
  `seat >= k` gets `+1`, **including inactive rows**, so an undo lands back in the right place.
- `session_performers.is_active` changes from "hasn't tapped Skip me" to "part of the night".
  The only thing that clears it is Remove.

The downgrade re-adds the four columns with their old defaults. Lap values aren't
reconstructable, and after a downgrade the lap model would rebuild them from new inserts
anyway.

## Backend

### `turn_service` owns the circle

This replaces the lap arithmetic in `turn_service.py` and the rotation half of
`queue_ordering.py`. `queue_ordering.get_ordered_queue_items` keeps the append-mode sort and
delegates rotation mode to the projection, so ordering still lives in exactly one place.

| Function | Does |
|---|---|
| `get_circle(db, session)` | Active performers by `seat` |
| `current_holder(db, session)` | The pointer's performer, else the lowest active seat. Read-only |
| `advance_pointer(db, session)` | Move to the next active seat, wrapping. Steps over anyone with `turns_borrowed > 0`, decrementing it as it goes. The only place borrowed turns are spent |
| `compute_turn(db, session_id)` | `bumped_item_id` if set, else the holder. Kinds: `queued` / `empty_seat` / `open`. Same `Turn` shape as today |
| `project_upcoming(db, session)` | The rotation-mode play order described above |
| `record_play(db, session, item)` | Called by `/play`. Handles: the bumped item (clear the bump, borrowed turn), the holder's song (advance the pointer), anyone else's song (borrowed turn) |
| `skip(session, holder)` | Advance the pointer |
| `insert_at_turn(db, session, performer)` | Renumber seats, place the performer at the pointer's seat, and point at them |
| `remove(db, session, performer)` | Deactivate, and advance the pointer if it was on them |
| `restore(db, session, performer)` | Reactivate, and point back at them |

**Where the pointer advances.** `/play` ([karaoke_queue.py:552](backend/app/api/karaoke_queue.py#L552))
is the only place playback moves to a new item (`/skip` clears the current song and
doesn't start the next). So `record_play` replaces `advance_to` there and nowhere else.

**Borrowed turns are spent when the pointer reaches them.** `advance_pointer` steps over and
decrements them when the pointer arrives at that person, not at play time. So a borrowed turn
always costs exactly the *next* turn, even if the circle changes in between. It also keeps
every write on a write path: `compute_turn` runs on every queue GET and broadcast, so it must
never mutate. The projection applies the same step-over rule without writing anything.

Only a non-holder can borrow. When the holder's own song is played or bumped, that's their
real turn, and `record_play` advances the pointer as normal.

**Rejoining.** `resolve_or_create_performer` on a *new* name appends at `max(seat) + 1`,
which is already what it does. On a *removed* name, it reactivates and moves them to the end
of the circle, following the "joining any other way" rule. The TV's Add performer path
instead calls `insert_at_turn`. `mark_active` keeps its role, but that role is now "come back
from Remove" rather than "come back from Skip me".

### Endpoints

All turn endpoints stay on `require_roster_access`, because guests operate the handoff
screen. They all keep `expected_performer_id` and answer 409 when the turn has already moved
on, which is the existing race guard between phone and TV.

| Endpoint | Change |
|---|---|
| `POST /sessions/{id}/turn/claim` | **Delete** ("That's not me") |
| `POST /sessions/{id}/performers/{pid}/deactivate` | **Delete** (old "Skip me for now") |
| `POST /sessions/{id}/turn/skip` | **New.** `{expected_performer_id}` |
| `POST /sessions/{id}/turn/insert` | **New.** `{expected_performer_id, name}`. Rejects a name that's already an active performer: they're already in the circle, and moving them isn't what this button means |
| `POST /sessions/{id}/performers/{pid}/remove` | **New.** `{expected_performer_id}` |
| `POST /sessions/{id}/performers/{pid}/restore` | **New.** `{expected_holder_id}`. The undo. It only points back at them if the turn is still where Remove left it, and otherwise just reactivates them |
| `POST /queue/{item_id}/bump` | Sets `bumped_item_id` instead of rewriting `lap` |
| `POST /queue/{item_id}/play` | `record_play` instead of `advance_to` |
| `POST /queue` (add) | Drop `compute_lap` / `enter_rotation` |
| Queue payloads (REST + WS) | Drop `lap` from items. `turn` keeps its shape; `circle` now starts at the holder |

## Frontend

| File | Change |
|---|---|
| [HandoffScreen.tsx](frontend/src/features/stage/screens/HandoffScreen.tsx) | Slot 3 becomes **Skip my turn** (primary) with **Add performer** and **Remove from rotation** (secondary) below it. The "That's not me" picker is gone. Add performer is a single name field. Typing a removed person's name brings them back through the same match |
| [useTurn.ts](frontend/src/hooks/api/useTurn.ts) | Replace `useClaimTurn` / `useDeactivatePerformer` with `useSkipTurn`, `useInsertPerformer`, `useRemovePerformer`, `useRestorePerformer`. Keep `TurnMovedOnError` |
| Remove's undo | A `sonner` toast with an Undo action calling `useRestorePerformer` |
| [SongConfirmScreen.tsx:42](frontend/src/features/stage/screens/SongConfirmScreen.tsx#L42) | **The walk-up bug.** The singer defaults to `roster[0]` (usually the host). Default to `turn.performerName` when there is one, else `roster[0]` |
| [QueueSingerDialog.tsx:80](frontend/src/features/songs/components/song-card/QueueSingerDialog.tsx#L80) | Same default, for the library path on a host device |
| [KaraokeQueue.ts](frontend/src/types/KaraokeQueue.ts) | Drop `lap` from the item type |

> `SongConfirmScreen.tsx` and `StageShell.tsx` have uncommitted changes from the song wheel
> work ([2026-09-25-stage-song-wheel.md](2026-09-25-stage-song-wheel.md)). Land the walk-up
> default after that, or coordinate. It's a one-line change, and it will conflict.

The walk-up fix doesn't depend on the model change and can ship first.

## Build order

1. **Walk-up singer default.** Frontend only, independent, and fixes the bug hit on the
   night. After the song wheel lands.
2. **Circle model + migration.** `turn_service` rewrite, projection, `record_play`,
   endpoints. Existing payload shapes hold, so the frontend keeps working with the old
   buttons wired to deleted endpoints. Ship 2 and 3 together.
3. **Handoff controls.** Skip / Add performer / Remove + undo.

## Not in this plan

- **A host roster list in Settings** (see who's removed, restore anyone, reorder seats).
  Leaving currently happens at the person's turn, which is where it gets noticed. Add the
  list if that proves insufficient.
- **Walk-ups as placeholder rows in the upcoming list** ("Patrick — picking at the TV").
  The projection can emit them cheaply, but the queue rail and phone UIs would need a
  songless row type.
- **Phone ETA** ("You're 3rd — about 11 minutes"), still from unit 4. It gets easier here,
  because the projection is already in order.

## Verification

**Backend**. Rewrite `tests/fastapi/test_queue_ordering.py` (rotation half) and
`tests/fastapi/test_turn.py`:

```bash
cd backend && source venv/bin/activate
alembic upgrade head
pytest tests/fastapi/test_queue_ordering.py tests/fastapi/test_turn.py
pytest
```

Cases that must be covered:
- Two people queue 5 and 3 songs in bursts → projection alternates from the top.
- Someone with nothing queued → `empty_seat` on their turn, every lap, until they pick or skip.
- Skip with songs in consecutive laps → no back-to-back.
- Insert at the pointer → new person is holder, displaced person is next, and the order
  holds on the following lap.
- Phone join mid-lap → sings after the highest seat, before the wrap.
- Remove → undo restores seat and pointer. Remove → play something → undo reactivates
  without stealing the turn.
- Play a song out of order → nobody else moves, and the pointer steps over that person
  exactly once.
- Bump during a song → that song is next, and then the pointer resumes where it was.
- Append mode → unaffected by all of the above.

**Frontend**. Run individually, never `pnpm run check`:

```bash
cd frontend
pnpm run type-check
pnpm run lint:check
pnpm run test:run
pnpm exec prettier --write "src/<only files touched>"
```

**End-to-end**, with a real session and three names seeded. Services run under tmux; do not
restart them (Celery isn't involved).

1. Nobody has queued → the screen names the first seat. Browse Library → confirm screen
   defaults to that person → sing → the next seat is named.
2. Skip someone with two songs queued → they come up next lap, one song per lap.
3. Add performer mid-night → they're up now, the person who was named is next, and the
   same order holds on the next lap.
4. Remove someone → toast → Undo → they're back and it's their turn again.
5. From the queue rail, play someone's song early → they're passed over once on the next lap
   and nobody else moves.
