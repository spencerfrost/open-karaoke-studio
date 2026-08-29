# Open Karaoke Studio - Tech Debt & Known Issues

Prioritized list of technical debt, known issues, and improvement opportunities discovered through codebase exploration.

## Summary Statistics

| Category | Count |
|----------|-------|
| **Critical Issues** | 5 |
| **Important Issues** | 10 |
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
