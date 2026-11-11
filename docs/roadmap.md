# Open Karaoke Studio - Roadmap

What's left to do. Built around how the app actually gets used: a living-room night with
5–10 people, a TV, a mouse on the mic stand, and phones.

The working plans behind these tasks are in `docs/plans/` in the repo, indexed by
`docs/plans/README.md`. They are internal and not part of this site.

**Last updated:** 2026-11-09

---

## Tasks

In no particular order.

- **Trustworthy vocal ranges.** The range on the song card and wheel comes from pyin frame
  percentiles, unchecked since it was built. Some are plainly wrong (Rick Astley up to A6, rap
  songs with sung ranges). Measure first (ear-check page, reference set, benchmark), then fix
  what counts as a note, label rapped songs, and show a comfortable range. *(Plan: vocal range)*
- **One keyboard layer for the stage.** Five screens each bind their own keys, with copies of
  the same checks that have already drifted apart (for example, holding Back on the confirm
  screen goes back twice). Replace them with one table of keys → actions and one hook.
  Navigation and the now-playing bar have landed, so nothing blocks it. Do it before the
  numpad mapping, which it turns into a one-table change. *(Plan: stage keyboard layer)*
- **Finish the guided demo.** The tour is built (see Done). Run it end to end in a browser,
  record the demo for **Watch the demo**, and publish the docs site so `VITE_DOCS_URL` can point
  the tour's links at it. On prod: the `jobs.step` migration, a Celery restart, and drop
  `DEMO_LOGIN_*`. *(Plan: guided demo)*
- **Rotation strip on the handoff screen.** "On deck" and the rotation line below it now
  list the same names in the same order. Replace both with one strip: each person's next
  turn for one lap, starting after whoever is up, with their next song (artwork and title)
  or a "no song yet" placeholder. End it with a "then Spencer again" marker, and dim anyone
  who will be passed over for having sung early. Nothing on it is clickable. The turn
  payload's `circle` entries need two new fields from the server: `nextItemId`, pointing
  into `upcoming`, and a passed-over flag. Still open: whether it also goes on song select,
  and matching the song wheel's card style.
- **Fold the domain docs into the docs site.** All six domain docs are written in
  `docs/domains/`. Cut `architecture.md` down to an overview that links to them, fold or delete
  what they duplicate in the other docs, add them to the sidebar, and add a rule that keeps each
  one current with its code. *(Plan: documentation mapping, integration pass)*
- **Render Mermaid in the docs site.** The docs-mapping plan assumes it, but VitePress needs
  `vitepress-plugin-mermaid` for that and it isn't installed. Until then the ingestion doc's
  diagrams show as raw code blocks.
- **Roll out artist credits on prod.** Built (see Done). Apply the migration, restart Celery,
  then Background jobs → Artist credits → Preview and read the report. Take a `pg_dump`, then
  Apply. The dev preview renamed some artists to MusicBrainz's current spelling ("Miley Cyrus"
  → "MILEY", "Fun." → "Fun"); decide whether to keep that rule before applying.
  *(Plan: artist credits)*
- **Run the new album cover lookup.** Restart Celery, run "Album covers" in all mode on dev,
  check the numbers, then prod after deploy. *(Plan: album and cover sources)*
- **Singer history.** Regulars want to see what they've sung so they remember what to sing
  next. Every performance is already logged by name; add a per-singer view on the phone,
  matched by name across nights. Then seed the handoff screen's suggestions from it, and
  build accounts only when names stop being good enough. *(Plan: singer history)*
- **Phone ETA** ("You're 3rd, about 11 minutes"). The rotation circle's projected order
  makes it a sum of song durations.
- **Repair the 54 AcoustID mislabels on prod.** Left over from the old tie bug. AcoustID no
  longer renames songs (`fc96274cf`), but it doesn't fix the ones it already got wrong.
- **Lyrics alignment runs say "done" too early.** A "Missing" or "Needs repair" run only queues
  one `align_song_lyrics` job per song, then marks itself done with every song counted, while
  the alignments themselves take hours. The Background jobs page should count a song as done
  when its alignment finishes, and keep the run open until the last one does.
- **Rework the song management dialog.** People open it to fix lyrics and run actions, not to
  edit details, but it opens on the details form and fills half its width. First the lyrics: a
  way to drop wrong synced lyrics so the plain ones win (the save already re-times them), the
  paste fix, and which lyrics the stage uses. Then the layout: two full-width columns with the
  song, its player and its actions on the left and the lyrics on the right.
  *(Plan: song management dialog)*
- **Cyberpunk and Catppuccin themes.** Two more themes to pick in Settings, for fun.
  *(Plan: cyberpunk and Catppuccin themes)*
- **New retro theme, vintage, cyberpunk as default.** The orange-gradient look becomes the
  "vintage" theme. "Retro" becomes a near-black page with cream text, orange buttons and three
  stripes under each header. Cyberpunk becomes the default. *(Plan: new retro theme)*
- **Stop blocking the event loop.** The login checks every protected route runs, the queue and
  session routes, the queue broadcast and the session WebSocket still make blocking database
  calls on the API's one event loop: the same cause as the October prod freezes. Make every
  route that uses the database plain `def`, send broadcasts from them through anyio, and keep
  one queue payload builder instead of two. A test fails when an async route takes the
  database. *(Plan: stop blocking the event loop)*
- **Make the database match the models.** About 50 differences between the models and the real
  Postgres schema, left by the SQLite conversion: columns the code treats as required that
  the database doesn't require, three unused columns, time-zone types. The tests run on
  SQLite, so they never see it. Read prod, fix the models where the database is right, write one
  migration for the rest, add a Postgres test that fails on new drift, and close
  [tech-debt](tech-debt.md) #33.
  *(Plan: database matches models)*
- **Backend file layout.** Group `services/` by domain, split `api/songs.py` and
  `api/sessions.py`, delete the unused interfaces, the job event chain and `jobs/jobs.py`. No
  behaviour changes. Waits for the singing map's commit. *(Plan: backend file layout)*

---

## Done

Shipped on `develop`. Some still need a check on the TV, noted below.

| Item | Commit | Left |
|---|---|---|
| Stage navigation: Enter/Back on the handoff screen, Back that knows the song ended, `L` for the songbook | `0b28ea903` (2026-09-29) | — (checked on the TV 2026-10-09) |
| Now-playing bar while browsing, and a 3-second fade when one song replaces another | `f1d926461`, `508492659` (2026-09-29) | The bar passed on the TV 2026-10-09. The fade failed: it stutters, then drops off fast. Re-check after the fix (a squared curve, not a straight line) |
| Rotation as a circle: seats, a turn pointer, Skip my turn / Add performer / Remove from rotation with undo | `935699503` (2026-09-29) | — (run on real nights) |
| Loudness rework: LUFS and true peak on the stems that play, a limiter, a backfill button | `63ec2ee86` (2026-10-09) | Deployed and backfilled 2026-10-09. Listen on the TV: a quiet acoustic song, a loud compressed one, a ballad with the lead vocal off |
| Stage song wheel, and artwork on it | `acc34ec32`, `e921b3631`, `6ec5a0c70`, `a3ec4fa09` (2026-09-25, 2026-10-09) | Fast spins read fine (no blur needed). The preview was too loud at half volume; re-check at a quarter. Still to tune on the TV: spacing, speeds, the settle before artwork loads, backdrop smoothness. Then decide whether song select can unmount |
| Wheel sources: a list of sources at the wheel's left, with **Recently added** (the last 100 songs) beside Artists A–Z | `1b582236d` (2026-10-25) | Try it on the TV: the source column's width and spacing, the two-line row height, whether far-back columns need hiding earlier |
| Song wheel opens fresh for the next singer once the song is 10% in; before that, and while someone is already browsing, it keeps its place | uncommitted (2026-10-26) | Try it on the TV: the remount once per singer should be quick |
| Lyrics reports: "Wrong words" / "Out of sync" from the Lyrics card, an admin tab, and "Report was wrong" | `e3ed399d1`, `d1acd1dfe` (2026-10-06) | Check on the phone and TV |
| Admin dashboard: full-width with a sidebar, one Background jobs page with progress and worker status, one list-and-song layout for review lists, a failed songs list, an overview | `eff9bd53c`, `ddc5a94d5`, `be0790e9a`, `8ebe721b7` (2026-10-09) | — (deployed 2026-10-09) |
| Album cover backfill: "Album covers" is now a job on the Background jobs page | `eff9bd53c` (2026-10-09) | — (run on prod 2026-10-09) |
| Worker status in admin: the overview and Background jobs page show which Celery queues have a worker | `eff9bd53c`, `8ebe721b7` (2026-10-09) | — |
| AcoustID suggests names instead of renaming songs; hand-set names are confirmed and left alone | `fc96274cf` (2026-10-09) | — (deployed 2026-10-09) |
| Lyrics `line_index` backfill confirmed on prod | Applied 2026-09-30 | — |
| Job tracker: a `step` on every job, an owner tag in place of the join code on `/ws/jobs`, the processing list with **Sing this** beside the wheel, inline progress on add-song results | `8114d6a91`..`04adfd06f` (2026-10-25) | Check the list's size and place on the TV |
| 3-2-1 countdown into every new song, holding on 1 until the audio is ready | `8e88de313` (2026-10-25) | Check on the TV |
| Phone opens the controls when its singer's song starts; "{Name}, open your phone" on the stage | `270403b8b`..`3c85ca20d` (2026-10-25) | Try on a real phone |
| "No phone? Open a phone view" under the join code: a guest window that keeps its own identity | `237e7633d`, `4e19bc025` (2026-10-24) | — |
| Live demo entry: **Try it live** (`POST /api/demo/start`) and **Watch the demo** on `/join`; real client IPs behind nginx | `b79f93f13`..`b8f9f506d` (2026-10-24, 2026-10-25) | Set `VITE_DEMO_RECORDING_URL` once the recording exists |
| Demo limits count finished downloads; demo accounts kept to the session the pool started | `b26a19906`, `d72aaa018` (2026-10-25) | — |
| Guided tour on the demo stage, moving on real app events, with a library-song fallback | `6878d3a6e`..`93ec3917c` (2026-10-25) | Run it end to end in a browser |
| Add song rebuilt around one search: a best match, other songs, covers under "other versions", artist and album screens, one preview player | `859323c72` (2026-10-25) | By hand on a phone and the stage: search, artist, album, back; add a song and watch its progress; two previews in a row; search with the network off |
| Phone controls: the phone gets its own layout with big faders, Earlier/Later timing and lyrics fixes in a sheet; the TV keeps its rail | `89a1bca23` (2026-10-25) | Try on a real phone in Safari and Chrome. On the TV, check the rail and the slower offset drag. Decide whether the TV rail uses the new words (Original singer, Backup singers, Earlier, Later) |
| Artist credits: one credit writer, artist ids and aliases, "Appears on" for featured-only artists, search through credited artists, a rebuild job | `a7cf4959d`..`554cf8b7a` (2026-10-25) | Prod rollout (see Tasks) |
| Lyrics alignment repair: offset sweep, word timings tied to their lyrics, sung language, re-timing from ASR, a "Needs repair" run | `6fb33accd`..`cfd252b9b` (2026-09-30 to 2026-10-09) | — (ran on prod 2026-10-10: 1,422 of 1,511 songs word-timed) |
| Theme switching from Settings, then text tiers, surface steps and decoration colors that every theme fills in | `d713e1592`, `4f33d4845`, `db6722ba2`, `dd83bbe85`, `82310e4b5` | — |
| Three-track engine ~3x faster with the same sound (58 → 20 s a song on the 3080 Ti) | `da371a7f2` (2026-10-10) | — |
| Backend tests: one folder for endpoint tests, job tests on real rows, coverage back over the gate | `08476ea1e`..`3ddcfde85` | — |

---

## Waiting for a trigger

Worth doing, but not until something makes them worth it.

| Item | Start it when |
|---|---|
| Three-track on a budget card | Buying the budget server card. The speed work has shipped (see Done) and already fits a 4GB card; on the new card, compare a song with autocast on and off. Further leads (the Demucs mix on the GPU, keeping models loaded between jobs) are in the archived plan |
| Key remapping in settings (numpad at the mic stand) | Buying the numpad, and after the stage keyboard layer. The host remaps stage keys on the TV in settings; the keyboard-layer plan's "Remapping later" section covers what it needs |
| NVIDIA Shield TV app | Built in `tv-app/` (`3bf489f1e`); needs trying on the Shield: log the remote's keys, then check the wrapper, sound on first play, and the server address and error screens. A WebView wrapper; the remote's keys are sent to the page as the stage's own keys |
| Auth gaps closed: library and proxy reads need an account or session, `/ws/jobs` authenticates, accounts reach only their own sessions, host-wide endpoints are admin-only, proxies are rate limited ([tech debt](tech-debt.md) #23, #25, #27, #28, #30, #32, #36, #37) | uncommitted (2026-10-28) | Try on a guest phone (join, browse, add a song, the processing list), stage recovery after a reload, and the recap playlist |

---

## Ideas

Not planned. Kept so they aren't lost. Anything that doesn't serve the living-room loop is
a low priority by default.

### During a performance
- **Song preloading.** The hook exists but is a TODO (`useKaraokePlayer.ts`). Would close
  the gap between songs.
- **Key transposition.** Shift a song up or down by semitones, saved per song.
- **Vocal effects** (reverb, echo) on the mic.
- **Screen transitions and sound effects** on the stage. `framer-motion` is already a
  dependency.
- **Attract screen** for when nobody is singing: join QR, recently played.
- **Vocal presets on the phone.** Big **Off / Quiet / Full** buttons ("Just you", "A guide",
  "Sing along") for the original singer, with a fine-tune slider under them, and a smaller
  row of the same for backup singers. A first-time guest picks a word instead of setting a
  fader. Mockup: option B on the
  [phone controls canvas](https://claude.ai/artifact/QrGduNZSDkqfqfRGzqMvm3).

### Lyrics
- **First-class lyrics, ongoing.** The [lyrics roadmap](https://github.com/spencerfrost/open-karaoke-studio/blob/master/docs/plans/2026-10-28-lyrics-roadmap.md) is
  a living plan for alignment quality, backing vocals, multiple singers, language-model line
  breaks, and benchmarking each new model as it comes out.
- **Verse/chorus line breaks** inferred from timing gaps in synced lyrics.
- **Align lyrics to the true vocal start**, ignoring intro "ooh"s the separation picked up.
- **An in-app LRC editor**: tap to set timestamps while the song plays.
- **Lyrics in their own table**, with type, source and alignment data, allowing more than
  one version per song. See [the lyrics analysis design](lyrics-analysis-system.md).

### Library
- **More wheel sources**: most sung, by decade. Each is another entry in the wheel's list of
  sources with its own columns. Build one when it's wanted.
- **Download progress** in the jobs list. There is none during the YouTube step today.
- **Bulk operations**: reprocess or re-tag many songs at once.

### Running the app
- **Backups** of the database and library.

### Code health
Longer-running items are tracked in [Tech Debt](tech-debt.md). The ones that affect
day-to-day work:
- `backend/app/api/songs.py` is over 1,900 lines and overdue for splitting.
- The frontend has 10 test files. Queue, session and player hooks have little coverage.
