# Reporting and fixing bad lyrics

Standalone. Not in the [sequencing](2026-08-29-sequencing.md) chain. Its first step has to ship
before step 5 of the [lyrics alignment repair](2026-09-29-lyrics-alignment-repair.md) runs on prod.

## Status (2026-09-30)

All four steps are built and committed on `develop`, not deployed. Checked on dev: a "Wrong words"
report on This Charming Man skipped the stored lyrics, stored LRCLIB's (score 0.49) and recorded
`replaced`; "Out of sync" re-timed the same words from ASR (0.72) and recorded `retimed`. Left:
checking the buttons on the phone and TV, the admin tab, and that the stage picks up a fix
mid-song.

| Step | State |
|---|---|
| 1. Remember rejected and hand-picked lyrics | Built. Migration `b7d41e9a2c58` applied on dev |
| 2. Report API, re-time-only runs and report outcomes | Built |
| 3. Report buttons on the Lyrics card | Built |
| 4. Admin Lyrics reports tab | Built |

### What changed from the plan while building

- **Hand-picked is a time, not a flag** (`songs.lyrics_hand_picked_at`). A run notes it, and the
  song's reports (ids and counts), when it starts. If either has changed by the time it writes, a
  person saved or reported the lyrics meanwhile: the run stops without writing and queues a fresh
  run. A run that finishes before the change also queues a fresh one. Without this, a guest who
  reports and then uses Search & Replace mid-run has their pick overwritten, and their lyrics never
  get timed (one run per song at a time).
- **No `retime_only` / `report_id` task parameters.** A run reads the song's pending reports (open,
  no outcome yet): only "Out of sync" pending → re-time the stored words; otherwise the full
  search. Afterwards each of those reports gets an outcome from what's on screen now: other words
  → `replaced` (`transcribed` if ASR's), same words newly timed → `retimed`, else `unchanged`. Any
  run (a fresh one after an interruption, a re-align, step 5's re-run) handles reports the same way.
- **The admin tab fixes lyrics in place** with the Search / Paste actions the Data Quality tab
  already uses (`SongActionPanel`), not a link to song details. Those saves go through the song
  PATCH, so they're hand-picked and re-timed.
- **The queue helper** moved to `backend/app/jobs/lyrics_dispatch.py` (`enqueue_song_alignment`,
  `realign_hand_picked_lyrics`). `POST /lyrics/songs/{id}` (lyrics text) marks hand-picked too.
- **Live refresh:** the jobs websocket now also invalidates `["lyrics", songId]` when a song's job
  finishes; the word timings are cached apart from the song.
- **"Report was wrong"** (added 2026-10-06, after testing on dev): a report keeps the lyrics on
  screen when it was first made (migration `c4f2a7e1b903`). The admin button puts them back,
  marks them hand-picked, re-times them and deletes the report, which lifts their rejection.
  Without it a mistaken "Wrong words" banned correct lyrics for good. Reports from before the
  migration have no copy; undoing them only lifts the rejection.

## Context

Bad lyrics are noticed by the person singing, but nobody can say so. Today:

```
who                       can do                                   timing afterwards
guest phone (/controls)   Search & Replace, Paste                  word timing wiped, never re-aligned
admin song details        fetch / paste / edit, Re-align button    only if they press Re-align
admin panel               metadata "flagged songs" audit           no lyrics checks
nobody                    say "these are wrong" / "try another"    -
nothing                   remembers rejected or hand-picked lyrics any re-run can bring them back
```

The last row matters for the lyrics alignment repair ([plan](2026-09-29-lyrics-alignment-repair.md)):
its step 5 re-runs the whole library, and a remote candidate that aligns replaces stored lyrics.
Without a memory, that re-run can overwrite lyrics someone fixed by hand and bring back lyrics
someone rejected.

Decided with Spencer (2026-09-30):
- **Anyone singing can report**: the performer's phone and the stage (both show the Lyrics card).
- **A report does both**: the app tries a fix straight away, and the song is listed for an admin.
- **Two kinds**: "Wrong words" (replace the text from another source) and "Out of sync" (keep
  the words, re-time them from the singing with step 4's ASR re-timing).
- **Guests keep Search & Replace and Paste**, but a replace now re-aligns.

## The design

```
 phone / stage Lyrics card                      admin: Lyrics reports tab
 ┌────────────────────────────┐                 ┌───────────────────────────────────┐
 │ Something wrong?           │                 │ Song · Wrong words · 2 reports    │
 │ [Wrong words] [Out of sync]│                 │ What the app did: replaced (lrclib)│
 └─────────────┬──────────────┘                 │ [Open song]  [Looks right now]    │
               │ POST report                    └───────────────────────────────────┘
               ▼                                               ▲
   lyrics_reports row (song, kind, words key, who, count)      │ open reports
               │                                               │
     ┌─────────┴───────────┐                                   │
 Wrong words           Out of sync                             │
 un-mark hand-picked   align_song_lyrics(retime_only)          │
 align_song_lyrics     → ASR re-time the stored text ──────────┤ outcome written
 (rejected words are     else unchanged                        │ to the report
  skipped as candidates)                                       │
 → next candidate that aligns, else re-time,  ─────────────────┘
   else (all rejected) ASR transcript

 Lyrics saved by a person (admin edit, guest Search & Replace / Paste)
   → hand-picked = true → re-align that text only (no remote candidates replace it)
```

**Rejected lyrics are remembered by their words**, not their formatting: a key from the lowercased
words in order (timestamps, punctuation and blank lines ignored), so the synced and plain copies of
the same lyrics from LRCLIB are both rejected. "Wrong words" reports are that memory: every
alignment run skips candidates whose key matches one, including the stored text. One row per
(song, kind, words key); a repeat report bumps its count and last reporter.

**Hand-picked lyrics** (`songs.lyrics_hand_picked`): set when any person saves lyrics text
through the song PATCH. Alignment of a hand-picked song only uses the stored text
(`include_remote=False`): align it, else re-time it, else show it untimed. A "Wrong words" report
clears the flag, since a person just said the pick is wrong. Existing songs start un-picked (no
history to go on).

**When every candidate is rejected**, the song counts as having no lyrics, so the ASR transcript
fallback applies (the one case step 4 keeps a transcript for). If ASR is unavailable, the
rejected lyrics stay on screen and the report stays open for an admin.

**Reports stay open until an admin marks them**, even when the automatic fix worked, because the
fix might be wrong too. The admin either confirms ("Looks right now") or opens the song and uses
the existing Lyrics tab.

## Changes

### Backend

- **Migration + models**: `lyrics_reports` (id, song_id FK cascade, kind `words`|`timing`,
  words_key, report_count, last reported by: user_id nullable + session_id nullable + display
  name, created_at, last_reported_at, outcome nullable `replaced`|`retimed`|`transcribed`|
  `unchanged`, resolved_at nullable, resolved_by user_id nullable). `songs.lyrics_hand_picked`
  boolean default false; add `lyricsHandPicked` to `Song.to_dict`. New model file next to
  `backend/app/db/models/song.py`, a repository next to `SongRepository`.
- **Words key**: `lyrics_words_key(content, source_type)` in
  `backend/app/services/lyrics_retiming.py`, built on the existing `lyrics_text_lines` and
  `_tokens` (same normalisation the matcher uses), hashed.
- **Skip rejected candidates**: `build_alignment_attempts` in
  `backend/app/services/lyrics_selection.py` takes `rejected_keys` and drops matching attempts
  (db ones too). `select_initial_lyrics` then can't re-store a rejected remote candidate.
- **Task** (`backend/app/jobs/lyrics_tasks.py`, `align_song_lyrics`):
  - Read `lyrics_hand_picked` and the song's rejected keys with the song snapshot.
  - Hand-picked → `include_remote=False`.
  - New `retime_only: bool`: skip as-is alignment and the sweep, go to `_retime_from_asr` on the
    stored candidates only.
  - New `report_id: int | None`: at every exit, write the outcome to that report.
  - All candidates rejected → the existing `no_candidates` transcript path.
- **API** (`backend/app/api/lyrics.py`):
  - `POST /lyrics/songs/{id}/reports` `{kind}`, `require_host_or_session_member` (as the song
    PATCH). Upserts the report on the current displayed text's key (synced, else plain), clears
    hand-picked for `words`, queues via the existing `_enqueue_song_alignment` (it already
    dedupes an in-flight job) with `retime_only` for `timing` and the `report_id`.
  - `GET /lyrics/reports?status=open` (host or admin), `POST /lyrics/reports/{id}/resolve`
    (host or admin).
- **Song PATCH** (`backend/app/api/songs.py`, `update_song`): when `plainLyrics` or
  `syncedLyrics` change, set `lyrics_hand_picked = True` and queue re-alignment with
  `include_remote=False` through `_enqueue_song_alignment` (move it to a service module so both
  routers use it without importing each other).

### Frontend

- **Report buttons**: a "Something wrong?" row in
  `frontend/src/features/performance/controls/LyricsControlsCard.tsx` (shown on the phone and
  the TV rail) with labelled buttons "Wrong words" and "Out of sync". Toasts in a guest's words:
  "Thanks — looking for better lyrics" / "Thanks — re-timing the lyrics to the singing".
- **Hook**: `useReportLyrics`, `useLyricsReports`, `useResolveLyricsReport` beside
  `frontend/src/hooks/api/useLyricsAlignment.ts`.
- **Admin tab**: `LyricsReportsTab.tsx` next to `LyricsAlignmentTab.tsx` in
  `frontend/src/features/songs/components/admin/`, registered in `frontend/src/pages/AdminPanel.tsx`. One row
  per open report: song, kind, count, last reporter and time, what the app did, the current
  lyrics source; "Open song" (existing song details, Lyrics tab) and "Looks right now". Kept
  plain: the admin UI is due an overhaul.
- **Live refresh**: lyrics job completion already invalidates the song query via
  `useJobsWebSocket`. Check that the playing song's lyrics re-render from it mid-song; if the
  player reads lyrics from the queue websocket payload (`backend/app/ws/queue.py`), broadcast a
  queue refresh when a lyrics job for the current song completes.

## Order

1. Backend memory: migration, words key, rejected-candidate skip, hand-picked flag, PATCH
   re-align. This is what step 5 needs.
2. Report API + task `retime_only` / `report_id`.
3. Report buttons on the Lyrics card.
4. Admin Lyrics reports tab.

Each ships on its own; 1 before the step 5 prod run.

## Verification

- Unit: words key ignores timestamps/punctuation/blank lines and matches plain vs synced copies;
  `build_alignment_attempts` drops rejected keys, including db candidates.
- Job tests (style of `backend/tests/jobs/test_lyrics_alignment_fallback.py`): a rejected stored
  text is skipped and the next candidate stored; all rejected → transcript; hand-picked uses no
  remote candidates; `retime_only` goes straight to re-timing; outcome written to the report.
- API tests (style of `backend/tests/integration/test_api/test_songs_api.py`): a session member
  can report; a repeat report bumps the count; hosts/admins list and resolve, others can't;
  PATCH with lyrics sets hand-picked and queues alignment.
- Backend: `pytest` from `backend/` with the venv. Frontend: type-check, lint and format run
  separately (not `pnpm run check`).
- Manual on dev (restart Celery first): from `/controls`, "Wrong words" on a song with an LRCLIB
  alternative → new lyrics appear on the stage without reload, report listed with outcome
  `replaced`; "Out of sync" → `retimed`; guest Search & Replace → word timing comes back; resolve
  in the admin tab.
