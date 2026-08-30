# Unit 3 — Roster + derived play order

Part of [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Depends on
[unit 1 — session lifecycle](2026-08-29-session-lifecycle.md). Runs **in parallel** with
[unit 2 — stage mode](2026-08-29-stage-mode.md); they meet at
[unit 4 — the handoff screen](2026-08-29-handoff-screen.md).

Design source: [The Rotation Problem](https://claude.ai/code/artifact/e8bcfb43-9e1b-4b5d-8bbf-12d242defb6c),
sections 01–04 and phases 1–2. This doc is the buildable version of that, reconciled against
what [unit 0](2026-08-29-kj-removal.md) actually deleted.

## Context

The queue cannot rotate fairly because the app has no idea who is in the room.
`KaraokeQueueItem` stores `singer_name` as a plain string
([queue.py](backend/app/db/models/queue.py)) — no foreign key to a person, a device, or a
user. The singer *is* the string.

Worse, the string comes from five places that do not agree:

| Source | What lands in `singer_name` |
|---|---|
| Phone joined via QR | The name typed on `QRJoinPage` → `sessionStore.displayName` |
| Phone joined via code form | `SessionJoinForm` never asks for a name at all |
| Play-now from any device | `displayName \|\| "Unknown Singer"` ([useSongActions.ts:63](frontend/src/features/songs/hooks/useSongActions.ts#L63)) |
| Suggestion tile after the queue empties | Literally `"Host"` ([QueueEnded.tsx:101](frontend/src/features/player/components/subcomponents/QueueEnded.tsx#L101)) |
| The unused constant | `DEFAULT_SINGER = "global"` ([singers.ts:12](frontend/src/constants/singers.ts#L12)) |

The only join between a queue item and a human is case-sensitive string equality on an
unnormalized field.

### The half that isn't an algorithm

This is the harder half and no scheduling algorithm touches it. When someone walks up to the
TV and browses the library on the stage device, everything they add is attributed to the
host — the person about to sing leaves no trace. **The rotation would be structurally blind
to exactly the people it exists to include.**

The fix is a roster that is **name-bound, not device-bound**. A roster entry can exist with
zero devices attached. That single decision buys three things: walk-ups become real people, a
couple sharing one phone becomes two people, and "add a song for my friend across the room"
becomes a name picker instead of a lie.

## Settled decisions

| Decision | Choice |
|---|---|
| Roster binding | **Name-bound**, not device-bound. Zero devices is a valid entry |
| Name matching | `lower(trim(name))`, store the display casing |
| Ordering modes | Two: `append` (today's behaviour) and `rotation` (strict round-robin) |
| Default mode | Rotation. Append is the escape hatch |
| Mechanism | One immutable `lap` integer per queue item, computed at insert |
| Rejected | Fair-share catch-up (unpredictable), turn-claim signup sheet (wrong shape) |
| Reordering | `Bump to next` in rotation mode; free drag stays in append mode only |

### Why strict rotation and not catch-up

These are easy to conflate. Catch-up equalizes *total songs sung*: Sarah arrives an hour
late having sung zero, the algorithm decides she is four behind and gives her four
consecutive turns. Technically fair, feels broken. Strict rotation puts Sarah into the circle
at the point the circle has reached — she waits one lap like everyone else, and nobody
accrues debt for turns they were not there for. Strict rotation is what people mean by "round
robin."

## Stage 3a — Give the app a roster

**No rotation yet. Ordering stays exactly as it is.** This stage is worth shipping whether or
not rotation ever follows.

### Schema

- **`SessionPerformer`** — new table, FK'd to `session_id`: `name`, `normalized_name`,
  `seat` (assigned on join), `laps_taken`, `is_active`, optional device link, and a
  **nullable `user_id`** for [unit 5](2026-08-29-performer-accounts.md). Add the nullable
  column now even though nothing reads it — it costs nothing and saves a migration.
- **`KaraokeQueueItem.performer_id`** and **`PerformanceHistory.performer_id`**, backfilled
  by normalized name from the existing `singer_name` columns. Keep `singer_name` for now as
  the display fallback.
- **`PerformanceHistory.user_id`** — nullable, denormalized at write time alongside
  `performer_id`. Sessions expire and roster rows get cleaned up, so lifetime history cannot
  hang off a session-scoped join or it dangles. Also added now, also unread until unit 5.
- **`KaraokeQueueItem.created_at`** — it does not exist ([queue.py](backend/app/db/models/queue.py)),
  yet both response builders guard with `hasattr(item, "created_at")` and the TypeScript type
  declares `addedAt: string` ([KaraokeQueue.ts](frontend/src/types/KaraokeQueue.ts)). `addedAt`
  has been `null` in every payload the app has ever sent. Add the column.

`SessionPerformer` rows are session-scoped, so they must be covered by unit 1's
`purge_stale_sessions` cascade — check that before writing the migration.

### Three entry points populate the roster

- **Phone join** — the QR path already collects a name; the code-form path
  (`SessionJoinForm`) needs to start asking.
- **Stage picker** — adding a song from the TV opens a grid of big name buttons for everyone
  already on the roster, plus *Someone else…* for one-off text entry. One tap, and the
  walk-up flow now produces identity. **This component is reused verbatim by unit 4's
  "That's not me"** — build it here, with that second caller in mind.
- **Host adds a name** — for the person who is definitely singing and definitely not
  touching a screen.

### What 3a ships on its own

Accurate performance history · walk-ups become visible · `addedAt` stops being a lie.

> The rotation design also listed "singer caps start working" here. **That benefit is gone** —
> [unit 0](2026-08-29-kj-removal.md) deleted `max_songs_per_singer` along with the rest of the
> KJ gatekeeping. Nothing in this stage should reintroduce a cap.

## Stage 3b — Derive the play order

### The mechanism: one immutable integer per queue item

```
# at insert time, in the ordering service
already_queued = count(performer's pending items)
lap = max(performer.laps_taken, session.current_lap) + already_queued

# play order — a pure sort, no mutation anywhere
sort queue by (lap, performer.seat, id)
```

**The `max()` is the whole trick.** A queue item can never be scheduled into a lap that has
already gone by, which handles the late joiner and the person who sat out a lap with the same
clause, without either building a backlog.

Because `lap` is written once and never recomputed, adding a song does not reshuffle other
rows, and the sort is stable and cheap. Append mode ignores `lap` and sorts by `id` — which
is why flipping modes mid-party is instant, reversible, and does not rewrite the table.

To be precise about what is immutable: **inserts never touch existing rows.** A deliberate
pass or bump rewrites `lap` on exactly one row, by hand, because a human asked — that is the
entire mechanism behind unit 4's pass-forward.

#### Worked example

| # | Singer | Seat | Lap | Why |
|---|---|---|---|---|
| 1 | Spencer | 0 | 0 | Queued 5 songs before anyone else touched a phone |
| 2 | Dan | 1 | 0 | Queued 5 a minute later — seat 1 breaks the lap-0 tie |
| 3 | Spencer | 0 | 1 | His 2nd song; one already queued, so lap 0 + 1 |
| 4 | Dan | 1 | 1 | His 2nd song |
| 5 | Spencer | 0 | 2 | Still alternating cleanly |
| 6 | Sarah | 2 | 2 | Walks up at lap 2. Seat 2, one song, `lap = max(0, 2) + 0` |
| 7 | Dan | 1 | 2 | Seat 1 < seat 2, so Dan precedes Sarah within lap 2 |
| 8 | Spencer | 0 | 3 | Circle is now three wide and keeps turning |

Sarah is not handed two catch-up songs for the laps she missed, and Spencer's five-song burst
never blocks anyone.

### Collapse the duplicated serializer

`build_queue_state()` (REST, [karaoke_queue.py:215](backend/app/api/karaoke_queue.py#L215)) and
`get_current_queue_state()` (WebSocket, [ws/queue.py:21](backend/app/ws/queue.py#L21)) are two
hand-maintained copies of the same serializer. They have already drifted once. **Ordering
logic has to live in exactly one place or it will drift again within a week** — introduce a
single `queue_ordering` service that both paths call, as part of this stage rather than after
it.

### Schema and state

- `lap` column on `karaoke_queue`, computed at insert. The row shape is clean for this —
  unit 0 already dropped `status`.
- `queue_order_mode` on the session (`append` | `rotation`), and `current_lap`.
- Everything keyed by `session_id`. No global dicts — see `.claude/rules/websocket.md`.

### What "reorder" means once ordering is derived

Free drag-and-drop and automatic rotation cannot coexist coherently — the next add undoes the
drag and nobody can tell what is manual and what is computed. Do not try to reconcile them.
In rotation mode, replace the drag with a single **Bump to next** action on any queue item.
One button, obvious effect, and it is what a host actually reaches for ("Grandma's leaving,
let her sing now"). Free reordering stays in append mode, where it already makes sense.

## Open decisions

**Where does the mode toggle live?** The design put it "in `HostDashboard`, next to the
queue-open and approval-mode controls that already live there." All three are gone. Candidates:
the Settings page (where unit 2 is already putting logout), or the `SessionInfoDisplay`
session panel. It must **not** go on the TV — see unit 4's "what stays off this screen."

**Does a roster entry ever expire?** Mostly answered by unit 4's *Skip me for now*, but that
only covers people who say so. For those who just leave: keep the seat, auto-deactivate after
two consecutive auto-passes, restore instantly on any activity.

**What happens when the roster is one person?** Rotation and append are identical for a solo
singer, which is correct — but the UI should not announce a "rotation" to an audience of one.
Recommendation: suppress the rotation ribbon below two active performers.

**Should queue endpoints verify device membership?** They currently trust the guessable
four-character code alone. [2026-07-09-auth-hardening-session-members.md](2026-07-09-auth-hardening-session-members.md)
already names this, and roster work touches the same handlers. Recommendation: fold it into
3a rather than visiting these endpoints a third time.

## Verification

**Backend**

```bash
cd backend && source venv/bin/activate
alembic upgrade head
pytest tests/                            # new: roster CRUD, lap computation, ordering service
pytest                                   # full suite
```

Unit-test the lap computation directly against the worked example above — it is pure and
cheap to cover, and it is the part that must not drift.

**Frontend** — run individually, never `pnpm run check`:

```bash
cd frontend
pnpm run type-check
pnpm run lint:check
pnpm exec prettier --write "src/<only files touched>"
```

**End-to-end** — services already run under tmux and hot-reload; do not restart them.

1. Join from two phones with different names → two roster entries, two seats.
2. Add a song from the TV → the name picker appears; pick *Someone else…* → a third roster
   entry with no device attached.
3. Queue five songs as one person and five as another → in rotation mode the play order
   alternates; flip to append → the original add order returns, instantly, with no reshuffle.
4. Join a third person mid-party → they enter at the current lap, and are **not** handed
   catch-up turns.
5. Confirm `addedAt` is a real timestamp in both the REST and WebSocket payloads — the same
   value from both, which is the regression test for the collapsed serializer.
