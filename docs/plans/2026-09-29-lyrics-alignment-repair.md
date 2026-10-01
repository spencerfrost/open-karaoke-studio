# Lyrics alignment repair

Standalone. Not in the [sequencing](2026-08-29-sequencing.md) chain. It touches the Celery lyrics
task, the alignment services, the admin Lyrics Alignment tab and prod data.

## Status (2026-09-30)

Steps 1–3 are done and committed on `develop`. **None of them is deployed to prod yet.** Step 4
is next, then step 5.

| Step | State |
|---|---|
| 1. Event log + line-index backfill | `6fb33accd`. Backfill applied to prod 2026-09-30 |
| 2. Lyrics and words from the same candidate | `3279cdf10` |
| 3. Align in the song's language | `229ea480a` |
| 4. Plain lyrics | Not started |
| 5. Library re-run from the admin tab | Not started. Needs 1–4 deployed first |

After the next deploy, check that `logs/lyrics_timing.jsonl` in the prod Celery container gets
lines with `song_id` and scores once a song is processed (step 1's fix).

### Where things are, for steps 4 and 5

- **Plain alignment path** (step 4): `run_alignment_attempt` in
  [lyrics_support.py](../../backend/app/jobs/lyrics_support.py) calls
  `align_plain_lyrics_to_vocals` for plain candidates. `_plain_lines_to_segments` is used there,
  in `align_plain_lyrics_to_vocals_with_model`, and in the plain branch of
  `recompute_alignment_line_indices` (all in
  [lyrics_alignment.py](../../backend/app/services/lyrics_alignment.py)). Step 2's
  `_fit_words_to_lyrics` calls `recompute_alignment_line_indices` with `source_type="plain"` when
  a plain candidate wins, so that path has to go when plain alignment goes.
- **Admin batch** (step 5): `batch_align_lyrics` in
  [batch_tasks.py](../../backend/app/jobs/batch_tasks.py) is the only user of
  `load_alignment_model` and the two `*_with_model` functions. Its API is `POST /api/lyrics/batch/align`
  in [lyrics.py](../../backend/app/api/lyrics.py), which still takes a `language` defaulting to
  `"en"`. The UI is `LyricsAlignmentTab.tsx` in `frontend/src/features/songs/components/admin/`.
- **"Needs repair" selection** (step 5): the 20 songs the old offset corrector touched aren't
  marked in the database. The audit found them from "offset corrected" outcomes in the prod Celery
  logs. The 50 songs whose words don't match their lyrics fail
  `recompute_alignment_line_indices`. 18 of them still have no `lyrics_source_type`.

### Working against prod

- Prod is the `karaoke-*-prod` Docker containers; its Postgres is on `localhost:15432`.
- Run scripts from `backend/` with the venv active and prod's URL, rewritten for the host:
  `export DATABASE_URL="$(docker exec karaoke-api-prod sh -c 'echo $DATABASE_URL' | sed 's#@postgres:5432/#@localhost:15432/#')"`
- Before any prod write: `docker exec karaoke-postgres-prod pg_dump -U karaoke_user -Fc karaoke > ~/karaoke-prod-<date>.dump`.
  Restore with `pg_restore --clean`.
- In agent sessions, read-only `psql` against prod has been allowed; running a script that can
  write to prod is blocked, so the user runs those.

## Why

Alignment and transcription run in the background after separation, and nothing showed whether
they worked. An audit of prod on 2026-09-29 (1,476 songs, Celery logs back to July 2025) found:

1. **The normal path mostly works.** Since 2026-05-19, 198 of 219 `align_song_lyrics` runs ended
   `ok`. 938 songs have word timings, and songs added since June are about 95% covered.
2. **Word timings that don't match the lyrics on screen, in about 1 song in 5.** Of about 935
   word-timed synced songs:
   - About 128 have the right words but point some at the next line. This is the WhisperX
     sentence-split bug fixed in `26a031665`. The offline backfill
     ([backfill_lyrics_line_index.py](../../backend/scripts/archive/backfill_lyrics_line_index.py))
     was archived as done, but prod still has the problem, so it probably only ran against dev.
   - About 47 have word timings whose text differs from the stored lyrics. One cause is in the
     code today (see step 2).
3. **The offset corrector made lyrics worse.** It read offsets from padded windows (hence
   corrections of exactly −8.0s and −3.0s) and applied them with the wrong sign. It also deleted
   the word timings every time. It ran 20 times since March. **Fixed in `3b5b3c4ad`**: see
   [lyrics-analysis-system.md](../lyrics-analysis-system.md#in-the-automatic-pipeline-the-whisperx-shift-sweep).
   The 20 songs it touched are still damaged.
4. **Alignment always runs in English.** The pipeline queues `align_song_lyrics` with only the
   song ID ([audio_tasks.py:326](../../backend/app/jobs/audio_tasks.py#L326)), so `language`
   defaults to `"en"`. Non-English songs score low and fall through to ASR, which can replace
   correct human lyrics with a transcription. French songs by Stromae are the known cases.
5. **Plain-lyrics alignment is nonsense.**
   [`_plain_lines_to_segments`](../../backend/app/services/lyrics_alignment.py#L528) gives line N
   a made-up window of 5N to 5N+5 seconds. WhisperX only searches the audio inside each window, so
   every word lands there. "Return Our Lives" is a 6-minute song whose word timings end at 0:57.
   Only 4 songs in prod are affected.
6. **413 songs have synced lyrics but no word timings**, almost all added before June. 46 have no
   lyrics at all. The Lyrics Alignment admin tab can re-run alignment, but its batch task
   ([batch_tasks.py](../../backend/app/jobs/batch_tasks.py#L186)) is a separate copy of the
   alignment logic. It has no offset sweep, no ASR fallback, and a different pass bar.
7. **ASR was broken from about March to late July** (a pyannote/torchaudio import crash). It has
   worked since 2026-07-31 but has only run 4 times.
8. **The lyrics event log has been empty since 2026-04-19.**
   [logging.py](../../backend/app/config/logging.py#L192) routes the logger named
   `app.lyrics_timing`, but [lyrics_timing.py](../../backend/app/services/lyrics_timing.py) logs as
   `app.services.lyrics_timing`, so its events only reach `app.log` mixed in with everything else.

## The design

Fix what stores bad data first, then re-run the library once. Any re-run before the fixes stores
the same bugs again.

After this plan, one song's alignment runs like this:

```
align_song_lyrics(song_id)
        │
        ▼
  language: song.language, else detect from vocals   ◄── step 3
        │
        ▼
  candidates: db synced, db plain, LRCLIB, syncedlyrics
        │
        ▼
  for each candidate, in order:
    synced → format, then strict alignment
    plain  → (step 4 decides)
    score ≥ 0.3 → store this candidate's lyrics AND its words together   ◄── step 2
        │
        ▼  none reached 0.3
  best synced candidate → shift sweep (±12s)   ◄── done, 3b5b3c4ad
    gain ≥ 0.03 and score ≥ 0.3 → store shifted lyrics + words
        │
        ▼  no usable shift
  ASR transcription in the song's language
```

The admin batch button queues this same task for each song instead of running its own copy.

## Steps

Each step ships on its own. Steps 2–4 change what gets stored, so they go before the re-run in
step 5. Steps 1 and 5 write to prod: take a `pg_dump` of `karaoke-postgres-prod` first.

### 1. Make it visible again, and repair line indexes

- Point the `file_lyrics_timing` handler at `app.services.lyrics_timing` in
  [logging.py](../../backend/app/config/logging.py#L192), or give the service logger the old
  name. Check that events land in `lyrics_timing.jsonl` inside the prod Celery container.
  **Done in `6fb33accd`.** It was also losing every field: the April change wrapped the logger in
  a `LoggerAdapter`, which replaces the call's `extra`, so since 2026-04-18 each event reached
  `app.log` as a bare name with no song ID or score. The service now uses a plain logger again.
  Tests: [test_lyrics_timing.py](../../backend/tests/unit/test_services/test_lyrics_timing.py).
- Run [backfill_lyrics_line_index.py](../../backend/scripts/archive/backfill_lyrics_line_index.py)
  dry-run against prod. Expect about 128 fixes. Apply it after checking the report. It needs no
  GPU and no audio.
  **Applied to prod 2026-09-30.** The first dry run skipped 639 songs: alignments from the April
  1–18 batch run don't store `lyrics_source_type`. The script now tries synced, then plain, and
  records the type it matched. Result: 131 songs relabelled (30,753 words), 621 got a source
  type, 50 skipped because their words don't match the stored lyrics (the step 2 problem; 18 of
  them are still untyped). Backup: `~/karaoke-prod-2026-09-30.dump`.

### 2. Store lyrics and words from the same candidate

- Today, when a later candidate (for example `lrclib:2`) is the one that aligns, the task stores
  its word timings, but `synced_lyrics` keeps whatever was stored first. `should_persist_synced_lyrics`
  in [lyrics_tasks.py](../../backend/app/jobs/lyrics_tasks.py#L633) only writes when the field was
  empty.
- Change: whenever a candidate's words are stored, its lyrics text is stored with them.
- Format every synced candidate before aligning it, not just the first remote one
  (`_persist_initial_lyrics_candidate` formats that one in place). Formatting inserts blank break
  lines, which renumbers lines.
- Add a check before any write: the stored words, read in order, must equal the tokens of the
  stored lyrics. If they don't, log it and don't store. This is the same check the audit used.
- Tests: a later candidate wins and its text replaces the stored text; the words/text mismatch
  guard.

**Done in `3279cdf10`.** Every save point (normal, offset-shifted, ASR) now goes through
`_fit_words_to_lyrics` in [lyrics_tasks.py](../../backend/app/jobs/lyrics_tasks.py): it re-derives
each word's line from the exact text being stored (the backfill's walk), and refuses words that
don't read as that text. A refused candidate is skipped and the next one is tried. ASR had the
same bug in another form: it numbered words by transcript segment, then formatting inserted break
lines, and words WhisperX couldn't time (numbers) were in the text but not the word list. ASR lines
are now built from their words ([lyrics_transcription.py](../../backend/app/services/lyrics_transcription.py)),
and if its words still don't fit, the transcript is stored without word timings.
Tests: [test_lyrics_candidate_storage.py](../../backend/tests/jobs/test_lyrics_candidate_storage.py),
[test_lyrics_transcription.py](../../backend/tests/unit/test_services/test_lyrics_transcription.py).

### 3. Align in the song's language

- Add `songs.language` (nullable, Alembic migration).
- When it's empty, detect the language from the vocals with the Whisper model the ASR fallback
  already loads (language ID on the first 30s), then store it.
- Pass it to alignment, the offset sweep and ASR.
- WhisperX only has alignment models for some languages. For a language without one, skip forced
  alignment and keep line-level lyrics.
- Show the language in song details, so a wrong detection can be corrected by hand.

**Done in `229ea480a`.** Migration `a3e8c1f6d920` (applied to dev; prod applies it on container
start, since `entrypoint.sh` runs `alembic upgrade head`). The task uses the
language asked for, else the song's, else detects it with faster-whisper on up to 90s of singing,
with silence skipped by its built-in VAD. A vocals stem's first 30s is often a silent intro.
Detections at ≥ 0.5 probability are stored; below that the run uses English and stores nothing.
On dev: both Stromae songs → `fr` (0.98, 0.77), Queen and QOTSA → `en` (0.74, 0.77).
Japanese and Chinese count as having no alignment model: WhisperX aligns them per character, and
step 2's check splits on spaces. The Details tab has a "Sung language" picker; changing it
re-queues alignment for that song. `GET /api/lyrics/languages` lists the codes. The admin batch
task still aligns in English until step 5 replaces it.
Tests: [test_lyrics_language.py](../../backend/tests/jobs/test_lyrics_language.py),
[unit](../../backend/tests/unit/test_services/test_lyrics_language.py), and the PATCH tests in
[test_songs_api.py](../../backend/tests/integration/test_api/test_songs_api.py).

### 4. Plain lyrics: stop pretending to align them

- Short term: don't run forced alignment on plain-only lyrics. Store the plain lyrics for display
  and let ASR produce timings.
- Better, if it's worth it: run ASR, then match its timed words to the plain lyrics text to give
  each plain line a timestamp. This makes synced lyrics out of plain ones without losing the human
  text. Decide after step 5 shows how many plain-only songs there are.
- Delete `_plain_lines_to_segments` and the plain `*_with_model` path along with the short-term
  change.

### 5. One re-run of the library from the admin tab

- Rewrite `batch_align_lyrics` to queue `align_song_lyrics` per song instead of aligning inline.
  Remove `align_lyrics_to_vocals_with_model` and `align_plain_lyrics_to_vocals_with_model` if
  nothing else uses them.
- Add a "needs repair" selection alongside "missing": songs with synced lyrics and no words, songs
  the old corrector touched, and songs failing the words/text check from step 2.
- Deploy, then run it on prod from the Lyrics Alignment tab. Expect about 413 + 20 + 47 songs,
  at about 5–60s each, on the `lyrics` queue.
- Re-run the audit numbers (see "Measuring it") and record them here.

## Measuring it

The 2026-09-29 baseline, from prod. Re-run the same queries after step 5.

| | Baseline |
|---|---|
| Songs with word timings | 938 of 1,476 |
| Synced lyrics, no word timings | 413 |
| No lyrics at all | 46 |
| Words point at the wrong line | ~128 |
| Words don't match the stored text | ~47 |
| Plain-lyrics alignments (nonsense timings) | 4 |
| `align_song_lyrics` outcomes since 2026-05-19 | 198 ok, 11 low confidence, 9 offset corrected, 1 no audio |

## Decisions made

- The offset sweep replaced the padded-window estimator (`3b5b3c4ad`). Thresholds: gain ≥ 0.03,
  score ≥ 0.3. On 7 known-good songs pushed off by −6…+9s, it was right in 35 of 35 cases.
- A remote candidate that aligns replaces the lyrics already stored (2026-09-30). Lyrics are only
  written by hand when no source has the song, so there's rarely a remote candidate to replace
  them. No hand-edit marker for now.
- The language is detected from the vocals, not taken from metadata (2026-09-30). Metadata is
  sparse; a wrong detection is fixed in song details.

## Open questions

- **Lyrics that don't match the recording** ("Not Too Late": a 3-minute song whose words run to
  about 10 minutes) still pass the 0.3 bar. Should word timings past the end of the audio count
  against the score?

## Not in this plan

- **Songs 1–2s off that still score ≥ 0.3.** They never reach the sweep. Catching them means
  sweeping every song (about 50s each). Decide after step 5 shows how many are left.
- **The manual `analyze/offset` endpoints** (RMS onset estimator). They work, with the opposite
  sign convention; leave them alone.
- **Consolidating the three lyrics layers** (plain / synced / word-synced). This plan removes
  some duplication but doesn't restructure them.
