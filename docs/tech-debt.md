# Open Karaoke Studio - Tech Debt & Known Issues

Prioritized list of technical debt, known issues, and improvement opportunities discovered through codebase exploration.

## Summary Statistics

| Category | Count |
|----------|-------|
| **Critical Issues** | 4 |
| **Important Issues** | 9 |
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

**Status:** 🚧 **Still Pending**

**Location:** [jobs_service.py:134](backend/app/services/jobs_service.py#L134)

**Problem:**
- UI has cancel button but backend doesn't actually cancel jobs
- Jobs marked as cancelled continue running
- Wastes system resources (CPU/GPU for audio processing)

**Evidence:**
```python
# TODO: Implement actual job cancellation in Celery
# This would involve celery.control.revoke(task_id, terminate=True)
```

**Impact:** HIGH - Resource waste, users think jobs are cancelled but they keep running

**Recommendation:**
```python
from celery import current_app

current_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
```

---

### 2. Print Statements in Production WebSocket Code

**Severity:** 🔴 CRITICAL

**Status:** ✅ **RESOLVED** (2026-03-06)

**Locations:** 5 files in `/backend/app/ws/`
- [session_specific.py](backend/app/ws/session_specific.py)
- [sessions.py](backend/app/ws/sessions.py)
- [connection_manager.py](backend/app/ws/connection_manager.py)
- [queue.py](backend/app/ws/queue.py)
- [jobs.py](backend/app/ws/jobs.py)

**Resolution:** All `print()` statements replaced with Python `logging` module. See `docs/websocket-protocol.md` for the complete WebSocket message catalog.

---

### 3. Type Safety Issues in Frontend

**Severity:** 🟡 MEDIUM

**Location:** [useJobsSync.ts:27](frontend/src/hooks/useJobsSync.ts#L27)

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

**Location:** [20251228_0009_d335baa6b48b_add_back_itunes_preview_url.py:23](backend/alembic/versions/20251228_0009_d335baa6b48b_add_back_itunes_preview_url.py#L23)

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
- [sessionWebSocketService.ts](frontend/src/services/sessionWebSocketService.ts) - WebSocket events
- [jobsWebSocketService.ts](frontend/src/services/jobsWebSocketService.ts) - Job updates
- [sessionStore.ts](frontend/src/stores/sessionStore.ts) - State changes
- [useKaraokePlayerStore.ts](frontend/src/stores/useKaraokePlayerStore.ts) - Player state

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
- [singers.ts:9-12](frontend/src/constants/singers.ts#L9-L12)
- [PrimaryActionsSection.tsx:56, 88](frontend/src/features/songs/components/song-details/PrimaryActionsSection.tsx#L56)

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

**Location:** [useKaraokePlayer.ts:111](frontend/src/features/player/hooks/useKaraokePlayer.ts#L111)

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

**Location:** [batch_test.py:39-43](backend/scripts/lyric_alignment/batch_test.py#L39-L43)

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

**Location:** [KaraokeQueueList.tsx:42](frontend/src/features/queue/components/KaraokeQueueList.tsx#L42)

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

**Location:** [useKaraokePlayer.ts:204](frontend/src/features/player/hooks/useKaraokePlayer.ts#L204)

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

**Location:** [useKaraokePlayerStore.ts:722](frontend/src/stores/useKaraokePlayerStore.ts#L722)

**Current State:**
```typescript
// Note: We don't reset the store state here as it causes infinite loops
```

**Investigation Needed:**
- Root cause of infinite loop
- Proper store lifecycle management
- Fix architecture vs working around it

---

### 13. Deprecated Test File Not Removed

**Severity:** 🟢 LOW

**Location:** [test_songs_api.py.deprecated](backend/tests/integration/test_api/test_songs_api.py.deprecated)

**Problem:**
- Old test file not deleted
- Clutters codebase

**Impact:** LOW - Code cleanliness

**Recommendation:**
- Delete file OR
- Restore if still needed

---

## Nice-to-Have Improvements

### 14. ESLint Disables Scattered Throughout Frontend

**Severity:** 🟢 LOW-MEDIUM

**Locations:** 9 occurrences of `eslint-disable` comments

**Files:**
- [Stage.tsx](frontend/src/pages/Stage.tsx)
- [AddSongDialog.tsx](frontend/src/features/songs/components/AddSongDialog.tsx)
- [LyricsFetchDialog.tsx](frontend/src/features/lyrics/components/LyricsFetchDialog.tsx)
- [FileUpload.tsx](frontend/src/components/FileUpload.tsx)
- [LibrarySearchInput.tsx](frontend/src/components/LibrarySearchInput.tsx)

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

**Location:** [KaraokeQueueItem.tsx:56](frontend/src/features/queue/components/KaraokeQueueItem.tsx#L56)

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

**Was:** `window.__playerWebSocketCleanup` global used for tracking WebSocket listener teardown in [useKaraokePlayerStore.ts](frontend/src/stores/useKaraokePlayerStore.ts).

**Fixed:** Replaced with a module-private `playerWebSocketCleanups` array. No longer pollutes the global namespace.

---

### 18. No Optimistic Updates for Songs

**Severity:** 🟢 LOW

**Location:** [useSongs.ts:183, 254](frontend/src/hooks/api/useSongs.ts#L183)

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
- Document WebSocket protocol in [docs/](docs/)
- Create architecture diagrams

---

## Quick Wins

These can be fixed quickly with high impact:

1. **Replace print() with logging** (1-2 hours)
   - Search and replace across backend
   - High impact on debuggability

2. **Remove console.log statements** (2-3 hours)
   - Replace with proper logging
   - Guard with debug flags

3. **Delete deprecated test file** (5 minutes)
   - Simple cleanup

4. **Implement Celery job cancellation** (1-2 hours)
   - Add revoke call
   - High user impact

5. **Fix default singer hardcode** (1 hour)
   - Add to localStorage
   - Quick UX improvement

---

## Recommended Priority Order

1. Fix global performance state (security/correctness)
2. Remove console.log/print statements (production readiness)
3. Add frontend test infrastructure (quality assurance)
4. Implement Celery job cancellation (resource management)
5. Fix type safety issues (code quality)
6. Complete preload implementation (performance)
7. Add settings feature for singer names (UX)
8. Implement queue drag-and-drop (UX enhancement)
9. Clean up experimental code (code organization)
10. Address ESLint warnings (code quality)

---

## Notes

- Many issues have TODOs already in code
- Backend is well-tested, frontend has 4 test files (infrastructure exists)
- Most critical issues are in WebSocket layer
- Many "nice-to-have" items are already tracked in code comments
- **New:** See [docs/websocket-protocol.md](websocket-protocol.md) for the complete WebSocket message catalog
- See [ROADMAP.md](ROADMAP.md) for how these fit into future plans
