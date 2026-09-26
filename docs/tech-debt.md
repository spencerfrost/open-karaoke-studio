# Open Karaoke Studio - Tech Debt & Known Issues

Prioritized list of technical debt, known issues, and improvement opportunities discovered through codebase exploration.

## Summary Statistics

| Category | Count |
|----------|-------|
| **Critical Issues** | 8 |
| **Important Issues** | 19 |
| **Nice-to-Have** | 7 |
| **Total TODOs Found** | 10+ explicit TODOs |
| **Console.log Statements** | 50+ in frontend |
| **ESLint Disables** | 9 |
| **Backend Tests** | 2,277 files |
| **Frontend Tests** | 4 files (infrastructure exists) |
| **Print Statements (Backend)** | 0 (resolved) |

**Note:** Several issues documented here have been resolved since this document was written. See [docs/websocket-protocol.md](websocket-protocol.md) for the current WebSocket message catalog.

---

## Table of Contents

1. [Critical Issues](#critical-issues) - Fix immediately
2. [Important Issues](#important-issues) - Address soon
3. [Nice-to-Have Improvements](#nice-to-have-improvements) - When time permits
4. [Quick Wins](#quick-wins) - Easy improvements

---

## Critical Issues

### 1. Celery Job Cancellation Not Implemented

**Severity:** 🔴 CRITICAL

**Status:** ✅ **RESOLVED** (commit `9d8368df4`)

**Location:** [jobs_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/jobs_service.py)

**Resolution:** `cancel_job()` now calls `celery.control.revoke(job.task_id, terminate=True, signal="SIGTERM")` before marking the job cancelled.

---

### 2. Print Statements in Production WebSocket Code

**Severity:** 🔴 CRITICAL

**Status:** ✅ **RESOLVED** (2026-03-06)

**Locations:** 5 files in `/backend/app/ws/`
- [session_specific.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/session_specific.py)
- [sessions.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/sessions.py)
- [connection_manager.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/connection_manager.py)
- [queue.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/queue.py)
- [jobs.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/jobs.py)

**Resolution:** All `print()` statements replaced with Python `logging` module. See `docs/websocket-protocol.md` for the complete WebSocket message catalog.

---

### 3. Type Safety Issues in Frontend

**Severity:** 🟡 MEDIUM

**Location:** [useJobsSync.ts:27](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/useJobsSync.ts#L27)

**Problem:**
- Type bypass with `as any`
- Compromises TypeScript type safety
- Runtime errors possible

**Evidence:**
```typescript
const songId = (job as any).song_id;  // Type bypass
```

**Impact:** MEDIUM - Runtime errors possible, type safety compromised

**Recommendation:**
- Define proper interface for job type
- Add `song_id` to job type definition
- Remove type bypass

---

### 4. Manual Migration Workaround

**Severity:** 🟡 MEDIUM

**Location:** [20251228_0009_d335baa6b48b_add_back_itunes_preview_url.py:23](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/alembic/versions/20251228_0009_d335baa6b48b_add_back_itunes_preview_url.py#L23)

**Problem:**
- Migration checks if column exists before adding
- Indicates prior manual ALTER TABLE fix
- Database schema inconsistency risk

**Impact:** MEDIUM - Database schema inconsistency across environments, migration ordering issues

**Recommendation:**
- Review migration history
- Ensure migrations are idempotent
- Document any manual database changes

---

### 22. `batch_align_lyrics` Crashes the Worker Process Mid-Batch (CUDA Allocator Corruption)

**Severity:** 🔴 CRITICAL

**Location:**
- [batch_tasks.py:batch_align_lyrics](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/jobs/batch_tasks.py) — loads the wav2vec2 model once, then loops synchronously over every eligible song (hundreds) inside a single Celery task invocation using `align_lyrics_to_vocals_with_model`/`align_plain_lyrics_to_vocals_with_model`.
- [gpu_idle_cleanup.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/gpu_idle_cleanup.py) — a `threading.Timer` that calls `torch.cuda.empty_cache()` after `GPU_IDLE_CLEANUP_SECONDS` of no tracked GPU activity, tracked via `begin_gpu_activity()`/`end_gpu_activity()`.
- [lyrics_alignment.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/lyrics_alignment.py) — the per-song `align_lyrics_to_vocals`/`align_plain_lyrics_to_vocals` (used by the single-song `align_song_lyrics` task) correctly bracket their CUDA work with `begin_gpu_activity()`/`end_gpu_activity()` (lines ~326/361, ~582/617). The `_with_model` variants used by `batch_align_lyrics` did **not** — the batch loop never told the idle-cleanup subsystem it was using the GPU.

**Problem:** Found 2026-08-28 while running a library-wide alignment backfill; the batch task repeatedly died with no error in `logs/celery.log` and no task-failure event. `journalctl`/`dmesg` showed the real cause: four separate hard SIGSEGV crashes in `libc10_cuda.so` (`DeviceCachingAllocator::malloc`, PyTorch's CUDA caching allocator) over the course of the backfill, each captured by `systemd-coredump`. Because `batch_align_lyrics` never called `begin_gpu_activity()`, a leftover idle-cleanup timer (armed by an unrelated task that had run earlier in the same worker process) could fire `torch.cuda.empty_cache()` on its own daemon thread *while the batch loop's thread was mid-allocation* — `empty_cache()` racing a live `cudaMalloc` on another thread of the same process corrupts the allocator's internal free-list, producing exactly this segfault signature. Because it's a native crash (not a Python exception), Celery can't catch it, log a traceback, or mark the task failed — the worker process just dies silently, and the batch stops with zero record of why.

**Impact:** CRITICAL — total, silent task loss. A multi-hundred-song backfill can die after processing only a handful of songs, with nothing in the logs to indicate why, and no automatic retry (the failure isn't visible to Celery as a failure at all).

**Fix applied (2026-08-28):** `batch_align_lyrics` now brackets its entire loop with `begin_gpu_activity("batch-lyrics-alignment:...")` / `end_gpu_activity(...)` in a `try`/`finally`, matching the pattern already used by the per-song alignment functions. This cancels/suppresses the idle-cleanup timer for the full duration of the batch instead of leaving it free to fire mid-batch.

**Follow-up still recommended:** restructure `batch_align_lyrics` into one Celery task per song — dispatched/chained the way `process_audio_job` already is — instead of one task looping over the whole library. This would also give proper per-song progress/retry instead of an all-or-nothing batch, and further reduce the blast radius if a similar native crash ever recurs from another cause.

**Related, lower-severity fix (same day):** added `--without-gossip --without-mingle` to all three workers in `run_celery.sh` — this stops noisy "missed heartbeat" log spam from cross-worker gossip on this single-box setup, but was a symptom fix, not the cause of the silent failures described above.

---

### 23. Most HTTP Endpoints Have No Auth Dependency At All

**Severity:** 🔴 CRITICAL

**Location:** `main.py:110-124` includes every router with no `dependencies=`, so per-endpoint `Depends(...)` is the *only* gate — there is no router-level or app-level fallback.

**Problem:** Found 2026-08-30 while rebuilding the frontend's access gate (the `isAuthenticated || sessionId` rule now enforced in `frontend/src/routes/guards.tsx`, replacing the passthrough left by commit `30e1f1882`). An inventory of every router turned up **~38 endpoints with no auth dependency whatsoever**, reachable by anyone who can reach the API — the entire read surface: every `GET /api/songs*` (list, search, artists, shows, by-artist, by-show, details, thumbnail, download), all of `lyrics.py`'s read endpoints, `youtube.py`/`youtube_music.py` search, and `sessions.py`'s `/info`, `/validate`, `/performers`. The frontend's route gate only controls what the React app *shows* — it does nothing to stop a direct `curl` against the API.

**Impact:** CRITICAL — on a LAN deployment this is low-severity (anyone on the network could already see the TV), but the app is not scoped to stay LAN-only, and several of these endpoints leak more than song metadata (see #24 and #25 below for the session-specific instances).

**Recommendation:** Apply `require_host_or_session_member` (`backend/app/api/dependencies.py`) across the read endpoints listed above, following the pattern already established for `POST /api/songs`, `PATCH /api/songs/{id}`, and `POST /api/youtube/download`. This is a large, mechanical change — worth its own PR rather than folding into unrelated feature work.

---

### 24. The Session WebSocket Accepts Unauthenticated Connects, and Two Handlers Are Ungated Inside It

**Severity:** 🔴 CRITICAL

**Location:** [session_specific.py:177-243](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/session_specific.py) (connect), lines 307-324 (`update_performance_control`), lines 448-454 (`queue_changed`).

**Problem:** Found 2026-08-30 during the same audit as #23. `/ws/session/{session_id}` checks only that the `KaraokeSession` row exists, is active, and isn't expired — no token, no `X-Device-ID`, nothing tying the socket to a real `SessionDevice`. The 4-character `session_id` (which is also the `display_code` shown on screen and printed in every QR code — see #29) is the only thing standing between an anonymous client and the room. An anonymous connection can passively receive every broadcast in the room (`session_connected`, `control_updated`, `performance_state`, `playback_*`, `queue_updated` — full singer names and song metadata) and can actively call `request_queue_update`.

Worse: the handler set is otherwise correctly gated on `is_session_owner` (see `update_player_state`, the `playback_play`/`playback_pause`/`reset_player_state`/`song_loaded`/`song_ready` group) — but two handlers were missed. `update_performance_control` has no ownership check at all and will write any key already present in the in-memory state dict, including `is_playing`, `current_time`, `duration`, and `current_song_id` alongside the intended volume/lyrics-size controls. `queue_changed` has no check either and lets any client trigger a `queue_updated` broadcast to the whole room.

**Impact:** CRITICAL — an anonymous client on the LAN can corrupt in-memory playback state and spam room broadcasts for a session it never joined, and can surveil every session's queue and singer names without a credential.

**Recommendation:** Add the same `is_session_owner` check already used by the sibling handlers to `update_performance_control` and `queue_changed`. The unauthenticated-connect design itself (vs. requiring a device credential at connect time) is a bigger decision — flag it for the same follow-up plan as #23 rather than deciding it here.

---

### 25. `/ws/jobs` Has No Auth Whatsoever

**Severity:** 🔴 CRITICAL

**Location:** [jobs.py:33-51](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/jobs.py)

**Problem:** Found 2026-08-30, same audit as #23-24. `manager.connect(websocket)` runs immediately on connect with no token check and no `authenticate` message handler at all — any anonymous client can connect, join the global `"jobs_updates"` room, and send `subscribe_to_jobs`/`request_jobs_list` to receive the full in-flight job list (`job.to_dict()`: filenames, titles, song ids, engine types). The equivalent HTTP endpoint, `GET /api/jobs`, requires `require_host` — this WebSocket is a straight bypass of that gate for read access.

**Impact:** CRITICAL — anonymous job-queue surveillance; the WS and HTTP surfaces enforce different policies for the same data.

**Recommendation:** Gate the connect (or at minimum the `subscribe_to_jobs` message) behind the same `require_host` check the HTTP endpoint uses.

---

## Important Issues

### 5. Missing Frontend Tests

**Severity:** 🟠 IMPORTANT

**Status:** 🚧 **In Progress** - Test infrastructure exists, coverage needs expansion

**Location:** `/frontend/src/` (entire frontend)

**Progress:**
- ✅ Vitest configured
- ✅ Mock data and API handlers added
- ✅ 4 test files exist (player store, LRC parser, lyrics timing, lyrics renderer)

**Current State:**
- 4 test files exist (not 0 as originally documented)
- Tests cover: player store, LRC parsing, lyrics timing/rendering
- Missing: queue operations, session connection lifecycle, WebSocket sync integration

**Recommendation:**
- Expand test coverage for critical paths: queue management, session lifecycle
- Add integration tests with mocked WebSockets
- Aim for 70%+ coverage of critical paths

---

### 6. Excessive Console Logging in Production

**Severity:** 🟠 IMPORTANT

**Status:** 🚧 **In Progress** - Using `createLogger()` but console.log still present

**Locations:** 50+ console.log statements across frontend

**Key Areas:**
- [sessionWebSocketService.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/services/sessionWebSocketService.ts) - WebSocket events
- [jobsWebSocketService.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/services/jobsWebSocketService.ts) - Job updates
- [sessionStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/sessionStore.ts) - State changes
- [useKaraokePlayerStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useKaraokePlayerStore.ts) - Player state

**Current State:**
- Logger utility exists (`createLogger` from `@/lib/logger`)
- Some files still use console.log directly
- Need to migrate all console statements to proper logging

**Recommendation:**
- Replace remaining console.log with createLogger
- Guard debug logging in production via `VITE_LOG_LEVEL`

---

### 7. Default Singer Hardcoded

**Severity:** 🟠 IMPORTANT

**Location:**
- [singers.ts:9-12](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/constants/singers.ts#L9-L12)
- [PrimaryActionsSection.tsx:56, 88](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-details/PrimaryActionsSection.tsx#L56)

**Problem:**
```typescript
// TODO: This should become a user setting in the upcoming settings feature
export const DEFAULT_SINGER = "global";
```

Also hardcoded "Unknown Singer" in action buttons.

**Impact:** MEDIUM - Poor UX, awaiting settings feature

**Recommendation:**
- Implement settings page
- Allow user to set default singer name
- Store in localStorage or user preferences

---

### 8. Incomplete Preload Implementation

**Severity:** 🟠 IMPORTANT

**Location:** [useKaraokePlayer.ts:111](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/hooks/useKaraokePlayer.ts#L111)

**Problem:**
```typescript
console.log("Preloading song:", preloadSongId);
// TODO: Implement actual preloading logic
```

**Impact:** MEDIUM - Performance optimization missing, songs not preloaded

**Recommendation:**
- Preload audio for next song in queue
- Use Web Audio API to buffer next track
- Reduce gap between songs

---

### 9. Disabled Lyric Alignment Analysis

**Severity:** 🟡 MEDIUM

**Location:** [batch_test.py:39-43](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/scripts/lyric_alignment/batch_test.py#L39-L43)

**Problem:**
- Analysis and reporting logic commented out with TODO
- Feature incomplete

**Impact:** MEDIUM - Technical debt in experimental code

**Recommendation:**
- Complete the implementation OR
- Move to separate experimental branch
- Document why it's disabled

---

### 10. No Drag-and-Drop Queue Reordering

**Severity:** 🟡 MEDIUM

**Location:** [KaraokeQueueList.tsx:42](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/queue/components/KaraokeQueueList.tsx#L42)

**Problem:**
```typescript
// TODO: add drag-and-drop functionality for reordering
```

**Impact:** MEDIUM - UX feature gap, users can't reorder queue easily

**Recommendation:**
- Use react-beautiful-dnd or @dnd-kit
- Add drag handles to queue items
- Update backend API to support reordering

---

### 11. Missing Connecting State in Player

**Severity:** 🟡 MEDIUM

**Location:** [useKaraokePlayer.ts:204](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/hooks/useKaraokePlayer.ts#L204)

**Problem:**
```typescript
return "disconnected"; // TODO: Add 'connecting' state detection
```

**Impact:** LOW-MEDIUM - Poor connection status feedback to users

**Recommendation:**
- Add 'connecting' state to player
- Show loading spinner during connection
- Better UX for connection issues

---

### 12. Player Store State Persistence Issue

**Severity:** 🟡 MEDIUM

**Status:** 🚧 **In Progress** - Workaround still in place

**Location:** [useKaraokePlayerStore.ts:722](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useKaraokePlayerStore.ts#L722)

**Current State:**
```typescript
// Note: We don't reset the store state here as it causes infinite loops
```

**Investigation Needed:**
- Root cause of infinite loop
- Proper store lifecycle management
- Fix architecture vs working around it

---

### ~~13. Deprecated Test File Not Removed~~ ✅ RESOLVED

**Was:** `test_songs_api.py.deprecated` left in `backend/tests/integration/test_api/`.

**Fixed:** File no longer exists in the repo.

---

### 21. Repeated Lyric Lines Break Word Alignment Matching

**Severity:** 🟠 IMPORTANT

**Location:**
- [lrcParser.ts:attachWordTimestamps](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/utils/lrcParser.ts) — frontend word-to-line matching
- [lyrics_alignment.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/lyrics_alignment.py) — WhisperX forced alignment

**Problem:** Found during manual testing (2026-08-28) while verifying a fix for partial-alignment rendering. Two distinct failure modes, same underlying trigger — a lyric line repeating verbatim elsewhere in the song:

1. **Duplicate-timestamp source data.** Some songs' `synced_lyrics` (from LRCLIB/`syncedlyrics`) have multiple distinct content lines sharing one identical `[mm:ss.xx]` timestamp — e.g. Atmosphere's "Fuck You Lucy" has ~12 consecutive lines all stamped `[00:53.90]`. `attachWordTimestamps`'s timestamp-based line matching can't distinguish between lines with identical timestamps, so word groups collapse onto the wrong line and duplicate/concatenate visually in the player.
2. **Wrong occurrence matched during forced alignment.** When the exact same lyric line/phrase occurs twice in a song (e.g. Cameron Whitcomb's "The Hard Way" repeats "(You were right) I had to do it the hard way" twice, ~12s apart), WhisperX's forced alignment can anchor word timing to the wrong occurrence, leaving one instance of the line with no word data while its twin has correct timing.

**Impact:** MEDIUM — cosmetic during karaoke playback (garbled/duplicated line text, or a line missing per-word highlighting) for the subset of songs with duplicate-timestamp LRC data or repeated lyric lines. Does not affect plain-lyrics or non-repeating synced-lyrics playback.

**Recommendation:**
- For (1): detect duplicate consecutive timestamps during LRC ingestion/parsing and either reject the source or fall back to evenly-spaced synthetic timestamps for that block.
- For (2): investigate whether WhisperX alignment can be given position/context hints (e.g. previous alignment progress) to disambiguate repeated phrases, or accept the limitation and only auto-apply alignment above a stricter per-song confidence threshold.
- Neither fix should be bundled with unrelated lyrics-rendering work — this is an alignment/data-quality problem, not a rendering bug.

---

### 26. `POST /api/sessions/{id}/performers` Is Unauthenticated

**Severity:** 🟠 IMPORTANT

**Location:** [sessions.py:969](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/sessions.py)

**Problem:** Found 2026-08-30 during the access-gate audit (see #23). Anyone who knows a session's 4-character id can inject arbitrary named performers into that session's roster and trigger a broadcast to every connected device — no membership or ownership check at all.

**Impact:** IMPORTANT — directly undercuts the roster feature ([docs/plans/2026-08-29-roster-and-rotation.md](https://github.com/spencerfrost/open-karaoke-studio/blob/acc34ec32/docs/plans/2026-08-29-roster-and-rotation.md)): a stranger can pollute a live session's singer queue.

**Recommendation:** Gate behind `require_host_or_session_member`, scoped to the named session the way `require_queue_access` now does for the queue endpoints (`backend/app/api/karaoke_queue.py`).

---

### 27. `POST /api/sessions/{id}/playlist` Is Unauthenticated

**Severity:** 🟠 IMPORTANT

**Location:** [session_playlist.py:135](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/session_playlist.py)

**Problem:** Found 2026-08-30, same audit as #26. An anonymous caller can trigger a background YouTube Music playlist-generation job for any session id, guarded only by an idempotent job id (not an auth check).

**Impact:** IMPORTANT — unauthenticated outbound work amplification against a third-party service.

**Recommendation:** Same fix shape as #26.

---

### 28. `GET /api/sessions/{id}/info` Leaks the Device Roster and Trusts a Client-Supplied `device_id`

**Severity:** 🟠 IMPORTANT

**Location:** [sessions.py:795-798](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/sessions.py)

**Problem:** Found 2026-08-30, same audit as #26. The endpoint returns the full connected-device roster (device ids, display names) to anonymous callers, and derives `is_host` by comparing `session.host_device_id` against a `device_id` passed as a plain query parameter — i.e. the client asserts its own host status and the server believes it for the purposes of this response.

**Impact:** IMPORTANT — anonymous roster/device-id disclosure, plus a spoofable `is_host` flag in the response (though nothing privileged is gated on this specific response's `is_host` today — worth re-checking if that changes).

**Recommendation:** Require the same credential (`X-Session-ID` + `X-Device-ID`) `require_session_member` already validates elsewhere instead of an unauthenticated query param.

---

### 29. `session_id` and `display_code` Are the Same Value — Anything Trusting the Id Alone Is Trusting a Displayed 4-Character Code

**Severity:** 🟠 IMPORTANT

**Location:** [session.py:96](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/db/models/session.py) — `session_id=display_code` at session creation.

**Problem:** Found 2026-08-30 during the same audit. `session_id` (the credential-shaped field used throughout the backend and the frontend's `sessionStore`) and `display_code` (the code printed on the stage screen and encoded in every QR code) are literally the same string. `_resolve_session_member` (`backend/app/api/dependencies.py`) is sound because it *also* requires the `rest_xxx`-prefixed `device_id`, but anything that trusts the session id by itself — the WS connect (#24), and `get_session_code` before this change (see `require_queue_access` in `backend/app/api/karaoke_queue.py`, which fixed this for the queue specifically) — is trusting a value that's designed to be shown on a TV and scanned from across a room.

**Impact:** IMPORTANT — not a bug by itself, but a footgun: the next endpoint or handler that reads for "is this caller in session X" by checking `session_id == X` alone is reintroducing the same hole #23's queue fix just closed.

**Recommendation:** When fixing #23/#24/#26/#27/#28, always pair the session id with the device credential (`_resolve_session_member`) or an account (`require_host_or_session_member`) — never trust `session_id` alone as proof of membership.

---

### 30. `require_host_or_session_member` Doesn't Fall Back to the Session Credential on an Expired Token

**Severity:** 🟠 IMPORTANT

**Location:** [dependencies.py:36-42, 137-159](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/dependencies.py)

**Problem:** Found 2026-08-30. `require_host_or_session_member` checks for a bearer token first; if one is present, `_resolve_user` raises `401` on an expired/invalid token and the function never falls through to the session-membership path — even though the caller may be holding a perfectly valid `X-Session-ID`/`X-Device-ID` pair. Concretely: a guest who signed into a host account at some point (token now expired, still cached client-side) loses queue/song-creation access despite an active session membership. Affects `POST /api/songs`, `PATCH /api/songs/{id}`, `POST /api/youtube/download`, and the new `require_queue_access` (`backend/app/api/karaoke_queue.py`) — anything built on this shared dependency.

**Impact:** IMPORTANT — a confusing, hard-to-reproduce access loss for a returning user; not a security hole (fails closed), just a broken fallback.

**Recommendation:** In `require_host_or_session_member`, catch the token-invalid case and continue to the session-membership check instead of raising immediately.

---

### 31. Host-Disconnect Session Teardown Is Keyed on the Socket, Not the User

**Severity:** 🟠 IMPORTANT

**Location:** [session_specific.py:467-510](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/session_specific.py)

**Problem:** Found 2026-08-30 during the same audit as #24. On `WebSocketDisconnect` of a connection with `is_session_owner=True`, a 30-second grace timer starts, after which `deactivate_session` + `force_close_session_connections` end the session for everyone. The timer is cancelled only when *some* connection re-authenticates as owner — but it's armed per-socket, not per-user, so a host with two tabs open who closes just one of them starts the countdown even though their other tab is still connected and still the owner.

**Impact:** IMPORTANT — a host can lose their live session (and kick every performer) just by closing a duplicate tab, with no warning.

**Recommendation:** Track "is the owning user still connected via *any* socket" rather than "did *this* socket reconnect within 30s" before arming or honoring the grace-period timer.

---

### 32. No Rate Limiting on the Unauthenticated Third-Party Proxy Endpoints

**Severity:** 🟠 IMPORTANT

**Location:** `/api/youtube/search`, `/api/youtube-music/*`, `/api/lyrics/search` (see #23 for the full unauthenticated-endpoint list).

**Problem:** Found 2026-08-30. Only `register`, `login`, `join-by-code`, and `join-by-id` carry `@limiter.limit`. Every unauthenticated endpoint that proxies to a third-party API — YouTube, YouTube Music, LRCLIB — has no rate limit at all.

**Impact:** IMPORTANT — an unauthenticated caller can drive unbounded outbound traffic to third-party services through this backend, which is both a cost/quota risk and a way to get the server's IP rate-limited or blocked upstream.

**Recommendation:** Extend the existing `@limiter.limit` pattern to these endpoints; fold in with #23 since fixing auth on them is the more fundamental change anyway.

---

### 33. `KaraokeSession.host_user_id` Is Optional, Forcing an Admin-Bypass Escape Hatch

**Severity:** 🟠 IMPORTANT

**Location:** [session.py:30](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/db/models/session.py)

**Problem:** Found 2026-08-30 while adding `require_session_owner` to `backend/app/api/karaoke_queue.py` (the ownership check behind `DELETE`/`reorder`/`play`/`skip` on the queue). Because `host_user_id` can be `NULL` on legacy rows, a strict "only the owner may mutate" rule would make those sessions permanently unmutable by anyone — the new dependency has to fall back to `current_user.is_admin` to avoid that trap.

**Impact:** IMPORTANT — not itself a vulnerability (the bypass is admin-only), but every future host-ownership check on `KaraokeSession` will need the same escape hatch until this is cleaned up, and each one is a place the bypass could be copied incorrectly.

**Recommendation:** Backfill `host_user_id` for any existing `NULL` rows (or confirm none exist in production) and migrate the column to `NOT NULL`, then drop the admin-bypass requirement from new ownership checks going forward.

---

### 34. Dead WebSocket Code: an Unrouted Session Endpoint and an Empty Module

**Severity:** 🟠 IMPORTANT

**Location:** [ws/sessions.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/sessions.py), `ws/session_state.py`.

**Problem:** Found 2026-08-30. `ws/sessions.py` defines a complete, unauthenticated session create/join-over-websocket endpoint (`websocket_session_endpoint`) that is neither exported from `ws/__init__.py` nor routed in `main.py` — unreachable in production, but live in the codebase as a second, divergent implementation of session join. `ws/session_state.py` is a 0-byte file.

**Impact:** IMPORTANT (maintainability, not runtime risk since it's unreachable) — dead code that could be mistaken for the real session-join path, or accidentally wired back in without the auth review the reachable paths have had.

**Recommendation:** Delete both files.

---

## Nice-to-Have Improvements

### 14. ESLint Disables Scattered Throughout Frontend

**Severity:** 🟢 LOW-MEDIUM

**Locations:** 9 occurrences of `eslint-disable` comments

**Files:**
- [Stage.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/Stage.tsx)
- [AddSongDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/AddSongDialog.tsx)
- [LyricsFetchDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/LyricsFetchDialog.tsx)
- [FileUpload.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/upload/FileUpload.tsx)
- [LibrarySearchInput.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/components/LibrarySearchInput.tsx)

**Problem:**
- `react-hooks/exhaustive-deps` disabled in multiple components
- Suppressing useful warnings
- Potential dependency bugs

**Impact:** LOW-MEDIUM - May hide bugs in useEffect dependencies

**Recommendation:**
- Review each case
- Fix dependency arrays properly
- Only disable if truly necessary

---

### 15. Missing Thumbnail Display

**Severity:** 🟢 LOW

**Location:** [KaraokeQueueItem.tsx:56](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/queue/components/KaraokeQueueItem.tsx#L56)

**Problem:**
```typescript
{/* TODO: Include thumbnail once that feature is finalized */}
```

**Impact:** LOW - Visual enhancement pending

**Recommendation:**
- Finalize thumbnail feature
- Add artwork to queue items

---

### 16. Error Handling Patterns Could Be Improved

**Severity:** 🟢 LOW-MEDIUM

**Locations:** Throughout frontend

**Problem:**
- Many `try/catch` blocks with simple `console.error()`
- No centralized error reporting/tracking
- No user-facing error messages

**Impact:** LOW-MEDIUM - Difficult to debug production issues

**Recommendation:**
- Implement error boundary components
- Add error tracking (Sentry, LogRocket, etc.)
- Show user-friendly error messages
- Centralized error handling

---

### ~~17. WebSocket Cleanup Management~~ ✅ RESOLVED (2026-03-06)

**Was:** `window.__playerWebSocketCleanup` global used for tracking WebSocket listener teardown in [useKaraokePlayerStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useKaraokePlayerStore.ts).

**Fixed:** Replaced with a module-private `playerWebSocketCleanups` array. No longer pollutes the global namespace.

---

### 18. No Optimistic Updates for Songs

**Severity:** 🟢 LOW

**Location:** [useSongs.ts:183, 254](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useSongs.ts#L183)

**Problem:**
```typescript
// Note: We don't optimistically update song lists due to complex query key structure
```

**Impact:** LOW - UX could be snappier

**Recommendation:**
- Implement optimistic updates
- Simplify query key structure
- Better perceived performance

---

### 19. Experimental Code in Production Repository

**Severity:** 🟢 LOW

**Locations:**
- `/backend/scripts/bpm_investigation/` - 8 experimental BPM detection strategies
- `/backend/scripts/ai_lyrics/asr_experiments/` - ASR model experiments
- `/backend/app/services/separation_engines/` - 3 experimental separation engines

**Problem:**
- Experimental code mixed with production code
- Not clearly marked or documented

**Impact:** LOW - Confusing, unclear what's production-ready

**Recommendation:**
- Move experiments to separate branch/repo OR
- Clearly mark as experimental in README
- Document which engines are production-ready

---

### 20. Documentation Gaps

**Severity:** 🟢 LOW

**Locations:**
- Complex lyrics rendering logic lacks inline documentation
- WebSocket message protocols not fully documented
- Session state management complexity not well-documented

**Impact:** LOW - Onboarding difficulty, maintenance burden

**Recommendation:**
- Add inline comments to complex logic
- ~~Document WebSocket protocol~~ — done, see [WebSocket Protocol](/websocket-protocol)
- Create architecture diagrams

---

## Quick Wins

These can be fixed quickly with high impact:

1. **Remove console.log statements** (2-3 hours)
   - Replace with proper logging
   - Guard with debug flags

2. **Fix default singer hardcode** (1 hour)
   - Add to localStorage
   - Quick UX improvement

---

## Recommended Priority Order

1. Remove remaining frontend console.log statements (production readiness)
2. Add frontend test infrastructure (quality assurance)
3. Fix type safety issues (code quality)
4. Complete preload implementation (performance)
5. Add settings feature for singer names (UX)
6. Implement queue drag-and-drop (UX enhancement)
7. Clean up experimental code (code organization)
8. Address ESLint warnings (code quality)

---

## Notes

- Many issues have TODOs already in code
- Backend is well-tested, frontend has 4 test files (infrastructure exists)
- Most critical issues are in WebSocket layer
- Many "nice-to-have" items are already tracked in code comments
- **New:** See [docs/websocket-protocol.md](websocket-protocol.md) for the complete WebSocket message catalog
- See [ROADMAP.md](/roadmap) for how these fit into future plans
