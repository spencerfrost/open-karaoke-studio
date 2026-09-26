# Documentation mapping — 6 chunks for parallel agents

## Why this doc exists

Spencer is the sole developer and is starting to feel lost in the codebase. The fix is
better documentation with diagrams, not one giant everything-diagram (133 non-primitive
frontend components alone makes a flat component graph unreadable). This doc splits that
work into 6 independent chunks, each buildable by its own agent with minimal file overlap
with the others. Point an agent at this file and tell it which chunk number to do.

**Chunks are vertical, not layer-split.** Early framing was "frontend vs backend," but a
feature is easier to understand end-to-end than split across two docs — so each chunk below
pairs a backend domain with its matching frontend feature. Chunk 6 is the exception: it's
what's left over after the five feature verticals (auth, app shell, cross-cutting state).

## Ground rules for every chunk

- **Output**: one new file at `docs/domains/<slug>.md` (create the `docs/domains/` folder).
  Do not edit `docs/architecture.md`, `docs/features.md`, or another chunk's file — a later
  integration pass folds these in and adds cross-links. Editing shared files from parallel
  agents is how you get merge conflicts.
- **Diagrams**: this is a VitePress site and renders Mermaid natively. Every chunk's doc
  needs at least one diagram (a component/module map for its slice, plus a sequence or flow
  diagram for anything with a multi-step process). Prose alone doesn't satisfy the brief.
- **Read before writing**: `docs/architecture.md` and `docs/features.md` already cover this
  codebase at a high level (written 2026-07-19). Don't contradict them silently — if the code
  has since diverged from what they say, say so explicitly in the new doc rather than quietly
  writing something that disagrees.
- **Scope discipline**: stick to the file list given for your chunk. If you find something
  load-bearing that belongs to another chunk, name it and move on rather than documenting it
  in place — that's what cross-references are for.
- **Don't paper over debt.** Two domains below are known to be messy (lyrics, song metadata
  provenance). Document what's actually there, including the mess, rather than describing an
  idealized version.

## The chunks

| # | Chunk | Output file | Depends on |
|---|---|---|---|
| 1 | Ingestion & processing pipeline | `docs/domains/ingestion-pipeline.md` | — |
| 2 | Song & library metadata | `docs/domains/song-library.md` | — |
| 3 | Lyrics system | `docs/domains/lyrics-system.md` | — |
| 4 | Sessions, queue & realtime | `docs/domains/sessions-realtime.md` | — |
| 5 | Player, stage & performance | `docs/domains/player-stage.md` | 4 (reads session state) |
| 6 | Platform foundations | `docs/domains/platform-foundations.md` | — |

All six can start in parallel; chunk 5 will read more sensibly once chunk 4 exists, but
doesn't need to wait for it.

---

### 1. Ingestion & processing pipeline

The YouTube download → Demucs separation → job-tracking flow — how a URL becomes karaoke
tracks.

- **Backend**: `api/youtube.py`, `api/youtube_music.py`, `api/jobs.py`; `services/youtube_service.py`,
  `services/youtube_music_service.py`, `services/jobs_service.py`, `services/audio.py`,
  `services/separation_engines/`, `services/chord_detection_service.py`,
  `services/gpu_idle_cleanup.py`, `services/file_service.py`, `services/file_management.py`;
  `repositories/job_repository.py`; `backend/app/jobs/`.
- **Frontend**: `pages/AddSong.tsx`, `pages/AdminThreeTrackComparePage.tsx`,
  `hooks/api/useYoutube.ts`, `hooks/useJobsSync.ts`, `hooks/api/useJobsWebSocket.ts`,
  `services/jobsWebSocketService.ts`, `services/uploadService.ts`,
  `stores/processingIndicatorsStore.ts`.
- **Cross-reference, don't duplicate**: the `/ws/jobs` WebSocket endpoint itself
  (`backend/app/ws/jobs.py`) belongs to chunk 4's realtime write-up — link to it rather than
  re-explaining the two-endpoint WS design.
- **Diagram**: a sequence diagram of one song's journey (URL submitted → job queued →
  Celery picks it up → separation engine runs → job completes → frontend notified).

### 2. Song & library metadata

Everything about what a song *is*: identification, enrichment, browsing, search.

- **Backend**: `api/songs.py`, `api/artists.py`, `api/albums.py`; `repositories/song_repository.py`,
  `repositories/artist_repository.py`, `repositories/album_repository.py`;
  `services/song_artist_service.py`, `services/artist_parsing.py`,
  `services/artist_image_service.py`, `services/musicbrainz_service.py`,
  `services/acoustid_service.py`, `services/itunes_service.py`, `services/credits_resolver.py`.
- **Frontend**: `features/library/`, `features/songs/` (the biggest single feature folder —
  46 components), `pages/Library.tsx`, `pages/AdminPanel.tsx` (its data-quality tabs:
  AcoustId, LibraryAudit, DataQuality, Duplicates — skip `LyricsAlignmentTab`, that's chunk
  3's), `hooks/api/useSongs.ts`, `stores/useSongsStore.ts`, `stores/useSongPreviewStore.ts`.
- **Known debt to document, not hide**: ~51 songs have wrong title/artist metadata from a bad
  batch AcoustID run — mention it as a known data-quality issue with the recovery tooling
  (`AcoustIdTab`) that exists for it. The `show_name` field for soundtracks/musicals is dead
  code — 0 of 900+ songs have it populated and there's no backfill path; say so rather than
  documenting it as a working feature.
- **Diagram**: a component map of `features/songs/` + `features/library/` (this one folder
  alone is a third of the frontend — a diagram here is where the "feeling lost" pain is
  worst), plus a flow diagram of metadata enrichment (fingerprint → AcoustID/MusicBrainz/
  iTunes → resolved credits).

### 3. Lyrics system

- **Backend**: `api/lyrics.py`; `services/lyrics_service.py`, `services/lyrics_selection.py`,
  `services/lyrics_analysis.py`, `services/lyrics_transcription.py`,
  `services/lyrics_offset.py`, `services/lyrics_timing.py`, `services/lyrics_alignment.py`,
  `services/syncedlyrics_service.py`.
- **Frontend**: `features/lyrics/`, `hooks/api/useLyricsAlignment.ts`, and the
  `LyricsAlignmentTab` in `pages/AdminPanel.tsx`.
- **Known debt to document, not hide**: this is three bolted-on layers (plain / synced /
  word-synced) with real duplication between them and no fix in progress. The doc's job is
  to make the actual layering legible — which layer a given code path touches, where they
  diverge — not to smooth it into something cleaner than it is.
- **Diagram**: a layer diagram showing the three lyrics representations, which
  services/components touch which layer, and where they currently overlap or duplicate logic.

### 4. Sessions, queue & realtime

- **Backend**: `api/sessions.py`, `api/session_playlist.py`, `api/karaoke_queue.py`;
  `services/session_service.py`; the entire `backend/app/ws/` folder (`connection_manager.py`,
  `session_specific.py`, `session_state.py`, `sessions.py`, `queue.py` — the two-WebSocket-
  endpoint design and the session-isolation invariant from `CLAUDE.md` live here).
- **Frontend**: `features/session/`, `features/queue/`, `stores/sessionStore.ts`,
  `contexts/SessionContext.tsx`, `services/sessionWebSocketService.ts`,
  `components/session/SessionInfoDisplay.tsx`, `pages/JoinSessionPage.tsx`,
  `pages/QRJoinPage.tsx`.
- **Important caveat**: this domain is mid-refactor right now — KJ removal shipped
  (`bfffe584f`), session lifecycle/stage-mode/rotation work is in flight per
  [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Date-stamp this doc as describing the
  **current, pre-refactor state**, and flag the specific pieces already known to be changing
  (`isHost`'s split into device-role vs. authority; host-disconnect deleting the session) as
  "documented as-is, expected to change" rather than presenting them as stable design.
- **Diagram**: a sequence diagram of the two WS endpoints (`/ws/jobs`, `/ws/session/{id}`)
  and connection lifecycle, plus a state diagram of session lifecycle (created → active →
  host disconnect → ended/expired).

### 5. Player, stage & performance

The live show experience — what's on screen while someone's singing.

- **Backend**: `api/performance_history.py`.
- **Frontend**: `features/player/`, `features/stage/`, `features/performance/`,
  `components/player/MiniPlayer/`, `pages/Stage.tsx`, `pages/PerformanceControlsPage.tsx`,
  `stores/useKaraokePlayerStore.ts`, `stores/usePlaybackStateStore.ts`,
  `stores/useAudioControlsStore.ts`, `stores/shared/audioHelpers.ts`.
- **Diagram**: a component map of the stage/player composition (what renders inside
  `StageLayout`), and a state diagram for playback (loading → playing → paused → ended →
  next-song handoff).

### 6. Platform foundations

Auth, host settings, and the shared app shell — what's left after the five verticals above.
Less "a feature" and more "how the app is wired together."

- **Backend**: `api/users.py`, `api/host_settings.py`; `services/auth_service.py`,
  `services/demo_service.py`.
- **Frontend**: `stores/authStore.ts`, `stores/useSettingsStore.ts`,
  `stores/useUIPreferencesStore.ts`, `components/auth/LoginForm.tsx`,
  `components/layout/NavBar.tsx`, `components/layout/AppLayout.tsx`, `App.tsx`,
  `pages/Settings.tsx`, `services/api.ts`.
- **Diagram**: an app-shell diagram — routes → layout → auth gate → the feature pages from
  chunks 1-5, showing where each one plugs in. This is the closest thing to the original "one
  big diagram" ask, but at the shell/routing level rather than every component.

## After all 6 land (not part of any single chunk)

A short integration pass — folding the six `docs/domains/*.md` files into `docs/architecture.md`
with cross-links, reconciling anything that contradicts the existing text, and adding the
domain files to the VitePress nav (`docs/.vitepress/config.ts`). Do this after, once there's
real content to integrate rather than a plan for it.
