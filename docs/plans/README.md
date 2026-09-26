# Plans

Live plans sit in this folder. Finished or replaced plans are in [archive/](archive/), each
with a banner at the top saying what shipped and when. `archive/` is gitignored, so it exists
only on the dev machine; git history has the files at their old paths. The stage / session / rotation work is
one dependency chain; start at [2026-08-29-sequencing.md](2026-08-29-sequencing.md).

Last audited 2026-09-25.

## Live

| Plan | Status |
|---|---|
| [Sequencing](2026-08-29-sequencing.md) | The index for the stage / session / rotation chain |
| [Rotation as a circle](2026-09-25-rotation-circle.md) (unit 3d) | **Next.** Not started. Step 1, the walk-up singer default, is unblocked now that the song wheel has landed |
| [Stage song wheel](2026-09-25-stage-song-wheel.md) | Built (`acc34ec32`). Step 5, tuning on the TV and deciding whether song select can unmount, is left |
| [Stage wheel artwork](2026-09-25-stage-wheel-artwork.md) | Built (`e921b3631`). Step 5, checking it on the TV (readability, backdrop smoothness, settle delay), is left |
| [Theme token migration](2026-07-19-theme-token-migration.md) | Stages 1–2 done. Stage 3 partial: ~140 raw palette classes left. Stages 4–5 not started |
| [Documentation mapping](2026-08-30-documentation-mapping.md) | 1 of 6 chunks done (`docs/domains/ingestion-pipeline.md`) |
| [Three-track VRAM optimization](2026-07-12-three-track-vram-optimization.md) | Not started |
| [Pre-production testing checklist](2026-08-28-pre-production-testing-checklist.md) | Out of date. Written at 40 unpushed commits; `develop` is now 114 ahead of `origin/develop` (last pushed 2026-07-09) |
| [Performer-seeded suggestions](2026-08-31-performer-seeded-suggestions.md) (unit 4b) | Deferred |
| [Performer accounts](2026-08-29-performer-accounts.md) (unit 5) | Deferred |

## Loose ends

Things archived plans promised that nobody owns yet.

- **Phone ETA** ("You're 3rd — about 11 minutes"), from the [handoff screen](archive/2026-08-29-handoff-screen.md).
  Rotation-circle lists it under "not in this plan".
- **A phone queues while the TV sits in song select** — does the TV move? Still open from
  [sequencing](2026-08-29-sequencing.md).

## Archive

| Plan | Shipped |
|---|---|
| [Library loading state + mobile fixes](archive/2026-03-07-library-loading-state-mobile-fixes.md) | Done, since reshaped |
| [Go TUI dev tool](archive/tui.md) | `cli/`, March 2026 |
| [Auth hardening](archive/2026-07-09-auth-hardening-session-members.md) | `59291ffb9` |
| [Demo account pool](archive/2026-07-09-demo-account-pool.md) | `7ce096045`, `176e79956` |
| [Stage redesign](archive/2026-08-28-stage-redesign.md) | `9726fda3e`, `d4935f37e` |
| [Unit 0 — KJ removal](archive/2026-08-29-kj-removal.md) | `bfffe584f` |
| [Unit 1 — Session lifecycle](archive/2026-08-29-session-lifecycle.md) | `b959d6b6d` |
| [Unit 2 — Stage mode](archive/2026-08-29-stage-mode.md) | `30e1f1882`, `a1d3a2ea5` |
| [Unit 3 — Roster + rotation](archive/2026-08-29-roster-and-rotation.md) | 3a `ebf33f50f`; 3b superseded by 3d |
| [Unit 3c — Create Session screen](archive/2026-08-30-create-session-screen.md) | `cb8489d18` |
| [Unit 4 — Handoff screen](archive/2026-08-29-handoff-screen.md) | `d2d197206`; turn controls superseded by 3d |
| [Lyrics alignment indexing](archive/2026-08-30-lyrics-alignment-indexing.md) | `26a031665` |
| [Unit 6 — Stage cabinet](archive/2026-08-30-stage-cabinet.md) | Never built. Replaced by the song wheel |
