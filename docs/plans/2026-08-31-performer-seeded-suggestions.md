# Performer-seeded suggestions

Split out of [unit 4 — the handoff screen](archive/2026-08-29-handoff-screen.md), which
ships with the suggestion tiles still seeded the old way. Depends on unit 4 having
landed; nothing else depends on this.

## Context

The handoff screen's empty slot asks a specific person to pick a song. Underneath
the name, it shows four tiles — and those tiles are seeded from **the song that
just finished**, by artist:

```ts
// useSongSuggestions.ts
const artistQuery = context?.currentSong?.artist;
```

So the screen says *"Sarah — pick something"* and then offers four more songs by
the artist the **previous** singer chose. The tiles are addressed to Sarah and
selected for whoever went before her. Unit 4's plan named this: *"Re-seeding from
the upcoming performer is genuinely new logic, not a prop rename"* — and
[useSongSuggestions](../../frontend/src/features/player/hooks/useSongSuggestions.ts)'s
own doc comment already lists *"songs the current user hasn't sung yet"* as an
intended next step.

It was cut from unit 4 to keep that unit to one screen and one state machine.

## Why the data is already there

Unit 3a added the two columns this needs and nothing has read them since:

- **`PerformanceHistory.performer_id`** — FK to `session_performers`, backfilled
  by normalized name ([performance.py](../../backend/app/db/models/performance.py)).
- **`PerformanceHistory.user_id`** — denormalized at write time, precisely so
  lifetime history survives the session-scoped roster row being cleaned up. That
  is the column that makes this work across nights rather than only within one.

`play_queue_item` already writes a history row per song
([karaoke_queue.py](../../backend/app/api/karaoke_queue.py)), so the data
accumulates today whether or not anything reads it.

## Shape

**Backend** — a read endpoint beside the roster ones in `sessions.py`:

```
GET /api/sessions/{session_id}/performers/{performer_id}/history
  -> [{songId, title, artist, performedAt}]
```

Scoped by `require_roster_access` like its neighbours. Query
`PerformanceHistory` by `performer_id`, and fall back to `user_id` when the
performer row carries one — that is the join that reaches last week's party.

**Frontend** — `SuggestionContext` gains an optional performer:

```ts
interface SuggestionContext {
  currentSong?: Song;        // becomes optional
  performerId?: number;      // preferred seed when present
  limit?: number;
}
```

Seeding order, best first:

1. **Artists this performer has sung before**, excluding songs they have already
   sung — the strongest signal, and the one people notice.
2. **The current song's artist** — today's behaviour, still right for a walk-up
   with no history.
3. **Recently added / popular** — the cold-start case, and the reason
   `SuggestionReason` already has `"popular"` and `"random"` variants that
   nothing emits.

`getSuggestionReasonText` needs one new reason (`"performer_history"` →
*"More like your last one"*), and the handoff screen passes
`turn.performerId` instead of `currentSong`.

## Worth deciding when this is built

- **A first-timer has no history**, and that is the majority of tiles early in a
  night. The fallback chain has to be genuinely good, not a placeholder — most
  of the value here is in tier 2 and 3 being decent.
- **Does the exclusion span the night or all time?** "Songs they have already
  sung" is obvious within a session; across nights it removes somebody's
  signature song from their own suggestions forever, which is wrong.
- **Suggestions on the phone too.** Once the seed is a person rather than a
  playing song, the same hook works on `PerformanceControlsPage`, where there is
  no "current song" context at all. That is probably the larger win.

## Verification

```bash
cd backend && source venv/bin/activate
pytest tests/fastapi/                     # new: history endpoint, user_id fallback

cd frontend
pnpm run type-check
pnpm run lint:check
pnpm run test:run
```

End-to-end: sing two songs by one artist as one performer, empty the queue, and
reach the handoff screen on their turn — the tiles should be seeded from *their*
history, not from whoever sang last. Then do the same for a brand-new name and
confirm the fallback still produces four sensible tiles.
