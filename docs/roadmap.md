# Open Karaoke Studio - Roadmap

What to build next and in what order. Built around how the app actually gets used: a
living-room night with 5–10 people, a TV, a mouse on the mic stand, and phones.

The working plans behind each step are in `docs/plans/` in the repo, indexed by
`docs/plans/README.md`. They are internal and not part of this site.

**Last updated:** 2026-09-25

---

## The order

```
 1. Finish in flight ──▶ 2. Deploy ──▶ 3. Rotation circle ──▶ 4. Domain docs
    wheel TV tuning        pre-prod       unit 3d, then         sessions and
    walk-up default        checklist      a real night          stage, after 3d
                           WS auth
                                                  ┆
 5. Background, any time:  theme migration stage 3 · docs for library, lyrics, platform
```

Each step unblocks the next. Deploy comes before the rotation rewrite on purpose: the
rewrite drops columns and replaces endpoints, and landing it on top of months of
unverified commits would make any production bug hard to place.

---

## 1. Finish what's in flight

**Size:** days

- **Tune the song wheel on the TV.** The wheel and its artwork are built (`acc34ec32`,
  `e921b3631`). What's left is checking them from the couch: the wheel's spacing and
  speeds, whether the 150ms settle before artwork loads feels natural, and whether the
  blurred backdrop runs smoothly. Then decide whether song select can unmount.
- **Walk-up singer default.** On the confirm screen and the host's queue dialog, the singer
  defaults to the first roster name (usually the host) instead of whoever's turn it is.
  This is the bug hit on the last night. It's one line in each place and doesn't wait on
  anything else.

## 2. Deploy

**Size:** a few days, mostly testing

Production is on `origin/develop` from 2026-07-09. Everything since then is local: the
stage, the roster, the handoff screen, the Create Session screen and the song wheel.

- **Rewrite the pre-production checklist.** The current one was written at 40 unpushed
  commits and it's now over 110. The riskiest parts are now the migrations (roster, lap,
  order mode) and the session lifecycle changes.
- **Close the WebSocket auth gaps first.** [Tech debt](tech-debt.md) #23–25: HTTP endpoints
  with no auth, the session WebSocket accepting anonymous connections, and `/ws/jobs` with
  none at all. They matter because the app is public and the demo login is meant to be
  shared. Queue and roster endpoints were scoped to session membership on 2026-08-30, so
  re-check #23–28 against the code before planning the work.

## 3. Rotation as a circle

**Size:** about a week, plus a night to test it

The core of how a night runs. Rotation today is a lap number on each queued song, and it
has two known bugs:

- Skipping someone who has songs in consecutive laps gives them back-to-back turns.
- Playing a song early moves the whole room forward, so people with nothing queued lose
  their turn.

The replacement is a fixed circle of seats and a pointer to whose turn it is. On the
handoff screen, "That's not me" and "Skip me for now" become **Skip my turn**, **Add
performer** and **Remove from rotation** with undo.

Build the backend and the new controls together, then take it to the next real gathering.
That night is the acceptance test.

## 4. Domain docs for sessions and the stage

**Size:** a day or two

One of six domain docs exists (ingestion pipeline). Write the sessions/realtime and
player/stage ones right after step 3, because step 3 rewrites that domain and docs written
before it would be stale within a week.

::: warning Diagrams
The docs-mapping plan assumes this site renders Mermaid. It doesn't: VitePress needs a
plugin for that, and none is installed. Add `vitepress-plugin-mermaid` before writing more
diagram-heavy docs, or the existing ingestion doc's diagrams stay as raw code blocks.
:::

## 5. Background work, any time

- **Theme migration, stage 3.** About 140 raw palette classes (`text-orange-peel` and
  friends) are left to replace with role tokens. It's mechanical and low-risk, good for
  gaps between bigger pieces. Stages 4–5 finish with the preset switcher and the dark neon
  default.
- **Domain docs for the song library, lyrics and platform.** These don't depend on step 3.
  Lyrics is the most useful of the three: it's the messiest system (plain, synced and
  word-synced lyrics are three separate layers with real duplication).
- **Confirm the lyrics `line_index` backfill ran.** The fix and its backfill script shipped
  on 2026-08-31. Nobody has checked the live library.

---

## Waiting for a trigger

Worth doing, but not until something makes them worth it.

| Item | Start it when |
|---|---|
| Three-track VRAM optimization | Buying the budget server card. The plan is written; all changes are opt-in env flags |
| Numpad mapping at the mic stand | Buying the numpad. The wheel already runs on arrows, Enter and Back |
| Phone ETA ("You're 3rd, about 11 minutes") | After step 3. The circle's projected order makes it a sum of durations |
| Suggestions seeded by the person whose turn it is | After step 3, once performance history per performer has built up |
| Performer accounts | Guests ask for favourites or their own history. Accounts grant conveniences, never capabilities |
| NVIDIA Shield TV app | After the numpad. A TV remote's D-pad sends the same keys |

---

## Ideas

Not planned. Kept so they aren't lost. Anything that doesn't serve the living-room loop is
a low priority by default.

### During a performance
- **Song preloading.** The hook exists but is a TODO (`useKaraokePlayer.ts`). Would close
  the gap between songs.
- **Key transposition.** Shift a song up or down by semitones, saved per song. Speed control
  already exists.
- **Loudness normalization** across songs, so one track isn't much louder than the next.
- **Vocal effects** (reverb, echo) on the mic.
- **Screen transitions and sound effects** on the stage. `framer-motion` is already a
  dependency. A 3-2-1 countdown could cover the audio load once autoplay settles.
- **Attract screen** for when nobody is singing: join QR, recently played.

### Lyrics
- **Verse/chorus line breaks** inferred from timing gaps in synced lyrics.
- **Align lyrics to the true vocal start**, ignoring intro "ooh"s the separation picked up.
- **An in-app LRC editor**: tap to set timestamps while the song plays.
- **Lyrics in their own table**, with type, source and alignment data, allowing more than
  one version per song. See [the lyrics analysis design](lyrics-analysis-system.md).

### Library
- **More wheel sources**: recently added, most sung, by decade. Each is a different set of
  columns. Build the second one when it's wanted.
- **Backfill album covers.** 557 albums have never been checked, so only 36% of songs have
  a cover.
- **Download progress** in the jobs list. There is none during the YouTube step today.
- **Bulk operations**: reprocess or re-tag many songs at once.

### Running the app
- **Worker health.** The enrichment worker has crashed without restarting before. A status
  line for Celery workers in the admin page would catch that.
- **Backups** of the database and library.

### Code health
Longer-running items are tracked in [Tech Debt](tech-debt.md). The ones that affect
day-to-day work:
- `backend/app/api/songs.py` is over 1,900 lines and overdue for splitting.
- The frontend has 10 test files. Queue, session and player hooks have little coverage.
