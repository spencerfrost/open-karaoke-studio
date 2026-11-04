# Open Karaoke Studio - Tech Debt & Known Issues

Known issues and cleanup work, grouped by severity. Item numbers are stable — other docs
link to them — so closed items keep their number in the [Resolved](#resolved) table and new
items take the next free number.

**Last checked against the code:** 2026-10-28.

| Severity | Open items |
|----------|-----------|
| 🟠 Important | #21, #31, #33 |
| 🟢 Low | #5, #8, #10, #11, #14, #16, #17, #18, #19 |

The access-gate audit items (#23–#37) are all fixed except #31 and #33, which are robustness issues,
not holes. [Authentication](/api/authentication) has the rules they settled on.

The 4-letter room code is the intended gate, Jackbox-style: anyone with the code may join. What
the audit items guard against is a path *around* the join step — something that accepts a code
without the rate-limited, roster-visible `join-by-code` that hands out a device id.

This page is the cross-cutting list. Each [domain doc](architecture.md#domain-docs) also has a
Known debt section with the bugs and dead code in its own slice, in more detail.

---

## Important Issues

### 21. Repeated Lyric Lines Break Word Alignment Matching

**Severity:** 🟠 IMPORTANT

**Location:**
- `frontend/src/utils/lrcParser.ts` (`attachWordTimestamps`) — frontend word-to-line matching
- `backend/app/services/lyrics_alignment.py` — WhisperX forced alignment

**Problem:** Found during manual testing (2026-08-28). Two failure modes, same trigger — a lyric
line repeating verbatim elsewhere in the song:

1. **Duplicate-timestamp source data.** Some songs' `synced_lyrics` (from LRCLIB/`syncedlyrics`)
   have several distinct lines sharing one `[mm:ss.xx]` timestamp — e.g. Atmosphere's "Fuck You
   Lucy" has ~12 consecutive lines stamped `[00:53.90]`. `attachWordTimestamps` now prefers the
   backend's `line_index`, but when that index
   isn't consistent it falls back to timestamp matching, which can't tell those lines apart, so
   words pile onto one line.
2. **Wrong occurrence matched during forced alignment.** When the same line occurs twice (e.g.
   Cameron Whitcomb's "The Hard Way" repeats "(You were right) I had to do it the hard way" ~12s
   apart), WhisperX can anchor word timing to the wrong occurrence, leaving one instance with no
   word data while its twin has correct timing.

The "Needs repair" alignment run (`backend/app/services/lyrics_repair.py`, 2026-10-09) catches
some of these through its `words_mismatch` reason and singer reports, but it re-runs the same
alignment, so it doesn't fix either cause. See
[lyrics-system.md](domains/lyrics-system.md) for how the matching works.

**Impact:** MEDIUM — cosmetic during playback (garbled/duplicated line text, or a line missing
per-word highlighting) for songs with duplicate-timestamp LRC data or repeated lines.

**Recommendation:**
- For (1): detect duplicate consecutive timestamps during LRC ingestion/parsing and either reject
  the source or spread synthetic timestamps across that block.
- For (2): investigate giving WhisperX position/context hints to disambiguate repeated phrases,
  or only auto-apply alignment above a stricter per-song confidence threshold.
- Keep both out of unrelated lyrics-rendering work — this is alignment/data quality, not rendering.

---

### 31. Host-Disconnect Session Teardown Is Keyed on the Socket, Not the User

**Severity:** 🟠 IMPORTANT

**Location:** `backend/app/ws/session_specific.py` (the `WebSocketDisconnect` handler)

**Problem:** Found 2026-08-30. When a connection with `is_session_owner=True` disconnects, a grace
timer starts; when it expires, `deactivate_session` + `force_close_session_connections` end the
session for everyone. The timer is cancelled only when *some* connection re-authenticates as
owner — but it's armed per socket, not per user, so a host with two tabs open who closes one of
them starts the countdown even though the other tab is still connected and still the owner.

**Impact:** IMPORTANT — a host can lose their live session (and kick every performer) by closing
a duplicate tab, with no warning.

**Recommendation:** Track whether the owning user is still connected on *any* socket before
arming or honoring the grace timer.

---

### 33. `KaraokeSession.host_user_id` Is Optional, Forcing an Admin-Bypass Escape Hatch

**Severity:** 🟠 IMPORTANT

**Location:** `backend/app/db/models/session.py:30`; the bypass is in
`backend/app/api/karaoke_queue.py:198`.

**Problem:** Found 2026-08-30. Because `host_user_id` can be `NULL` on legacy rows, a strict
"only the owner may mutate" rule would make those sessions unmutable by anyone — so
`require_session_owner` falls back to `current_user.is_admin`.

**Impact:** IMPORTANT — not a vulnerability (the bypass is admin-only), but every future
ownership check on `KaraokeSession` needs the same escape hatch until this is cleaned up, and
each copy is a place it could go wrong.

**Recommendation:** Backfill `host_user_id` for any `NULL` rows (or confirm none exist in prod),
migrate the column to `NOT NULL`, then drop the admin bypass.

---

## Low Priority

### 5. Thin Frontend Test Coverage

**Severity:** 🟢 LOW-MEDIUM

**Current state:** 13 test files, covering the player store, LRC parsing, lyric timing and
rendering, route guards, `useAccess`, the stage wheel model, turn items, the default-singer
picker, and a few utils.

**Missing:** queue operations, session connection lifecycle, WebSocket sync — the paths most
likely to break during a live session.

**Recommendation:** Add tests for the queue and session hooks with a mocked WebSocket.

---

### 8. Preload Is a Stub

**Severity:** 🟢 LOW

**Location:** `frontend/src/features/player/hooks/useKaraokePlayer.ts` (`preloadSong`)

**Problem:** `preloadSong` only logs and has a `// TODO: Implement actual preloading logic`. No
caller passes the `preload` option (`KaraokePlayer.tsx` passes only `autoPlay`), so it never runs.

**Recommendation:** Either implement it (buffer the next queued song's stems so the handoff has
no load gap) or delete the stub and the `preload` option.

---

### 10. No Queue Reordering in the UI

**Severity:** 🟢 LOW

**Problem:** The backend supports `PUT /api/karaoke-queue/reorder` (append mode) and bump
(rotation mode), but no frontend code calls either. The old `KaraokeQueueList` and its
drag-and-drop TODO are gone; the queue is now shown by `StageQueueRail`.

**Recommendation:** Decide whether the host needs manual reordering now that rotation mode
exists. If yes, add bump/reorder controls; if no, consider removing the unused endpoints.

---

### 11. Missing Connecting State in Player

**Severity:** 🟢 LOW

**Location:** `frontend/src/features/player/hooks/useKaraokePlayer.ts` (`connectionStatus`)

**Problem:** `return "disconnected"; // TODO: Add 'connecting' state detection` — the type allows
`"connecting"` but it's never returned, so a reconnect looks like a disconnect.

**Recommendation:** Derive `connecting` from the session WebSocket service's state.

---

### 14. ESLint Disables

**Severity:** 🟢 LOW

**Locations:** 6 `react-hooks/exhaustive-deps` disables:
- `components/ui/file-uploader.tsx:157`
- `features/songs/components/admin/panels/FingerprintLookupPanel.tsx:37`
- `features/stage/wheel/useWheelPreview.ts:42`
- `pages/AdminThreeTrackComparePage.tsx:656, 668`
- `pages/Entry.tsx:78`

**Recommendation:** Review each; fix the dependency array or leave a comment on why the disable
is correct.

---

### 16. Error Handling Patterns

**Severity:** 🟢 LOW

**Current state:** The player has an error boundary (`PlayerErrorBoundary`) and songs have a
shared error-message helper (`features/songs/utils/errorMessage.ts`), but there's no app-level
error boundary, and many catch blocks only log.

**Recommendation:** Add a route-level error boundary, and show user-facing messages where a
catch currently only logs.

---

### 17. Player WebSocket Listeners Stack Up

**Severity:** 🟢 LOW

**Location:** `frontend/src/stores/useKaraokePlayerStore.ts` (`connect`)

**Problem:** `connect()` registers nine `sessionWebSocketService` listeners and stores their
cleanups on `window.__playerWebSocketCleanup`, overwriting any earlier set without running it. Both
`useKaraokePlayer` (the stage) and `useSessionConnection` (the phone) call it, so each remount of
`KaraokePlayer` adds another set and a remote `playback_play` calls `play()` once per set.

**Recommendation:** Run the existing cleanups at the top of `connect()`, and keep them in a
module-level variable instead of on `window`.

---

### 18. No Optimistic Updates for Songs

**Severity:** 🟢 LOW

**Location:** `frontend/src/hooks/api/useSongs.ts:194, 266`

**Problem:** `// Note: We don't optimistically update song lists due to complex query key structure`

**Recommendation:** Simplify the song-list query keys, then add optimistic updates.

---

### 19. Production Separation Engines Are Labeled "Experimental"

**Severity:** 🟢 LOW

**Location:** `backend/app/services/separation_engines/__init__.py`

**Problem:** The package docstring says "Experimental vocal separation engines for benchmarking",
but `app/jobs/jobs.py` and `app/jobs/separation.py` import from it — it's the production
separation code. It's not clear which of the seven engines are actually selectable in production
and which are only benchmark variants.

The rest of the original item is done: the BPM experiments were removed (2026-09-03), and
`backend/scripts/README.md` marks `scripts/experiments/` as unmaintained research code.

**Recommendation:** Rewrite the docstring to say which engines production uses; move
benchmark-only engines to `scripts/experiments/` if any are unused.

---

## Resolved

| # | Item | How it was closed |
|---|------|-------------------|
| 1 | Celery job cancellation | `cancel_job()` revokes the Celery task before marking the job cancelled (`9d8368df4`). |
| 2 | `print()` in WebSocket code | Replaced with `logging` (2026-03-06). |
| 3 | `as any` in `useJobsSync.ts` | `job.song_id` is typed; no `as any` left in the frontend. |
| 4 | Defensive `itunes_preview_url` migration | Won't fix: the existence check is in an already-applied migration and is harmless; editing applied migrations is riskier than leaving it. |
| 6 | Console logging | No direct `console.*` calls outside `lib/logger`; the logger defaults to `warn` in production (`VITE_LOG_LEVEL` overrides). |
| 7 | Hardcoded default singer | `DEFAULT_SINGER` is gone; the singer picker starts on the current turn's performer (`useDefaultSinger`). |
| 9 | Disabled analysis in `batch_test.py` | Covered by `backend/scripts/README.md`: `experiments/` is unmaintained research code. |
| 12 | Player store reset workaround | The "don't reset, causes infinite loops" workaround went away when the store was split into sub-stores (`461b44fc6`). |
| 13 | Deprecated test file | Deleted. |
| 15 | Missing queue-item thumbnail | `KaraokeQueueItem` no longer exists; the queue is shown by `StageQueueRail`. |
| 20 | Documentation gaps | WebSocket protocol, architecture and per-domain docs (`docs/domains/`) now exist. |
| 22 | `batch_align_lyrics` crashing the worker | GPU activity bracketing added 2026-08-28; since 2026-10-06 the batch queues one `align_song_lyrics` job per song, so a crash loses one song, not the batch. |
| 23 | HTTP endpoints with no auth dependency | Library, lyrics, YouTube and YouTube Music reads need an account or session credential (`require_host_or_session_member`). Media URLs (thumbnails, covers, artist images, track files) stay header-free for `<img>`/`<audio>`: song ids are random UUIDs, learned only through the gated reads, and covers and artist images are public artwork. `/api/performance-test` deleted. |
| 24 | Session WebSocket accepted anyone with the code | The first message must be `authenticate` with an active member device id; wrong code and wrong device get the same `not_a_member` + close 1008, so the socket can't find live codes. `update_performance_control` is limited to the mix/display controls, and the `queue_changed` relay is gone (2026-10-10). |
| 25 | `/ws/jobs` had no auth | The first message must be `authenticate` with an account token or a session member's `session_id` + `device_id`; anything else gets `auth_failed` and close 1008. The frontend client opens the socket once it holds credentials and reconnects when they change. |
| 26 | Unauthenticated `POST /sessions/{id}/performers` | `GET` and `POST` now go through `require_roster_access`, which confines anonymous guests to their own session. |
| 27 | Unauthenticated session playlist endpoints | `POST` is the session's host or an admin only (it writes to the server's YouTube Music account); `GET` goes through `ensure_session_access`. |
| 28 | `GET /sessions/{id}/info` leaked the roster and trusted `?device_id=` | Requires the session credential, the hosting account or an admin (`ensure_session_access`); `is_host` comes only from the account, `is_self` from `X-Device-ID`. |
| 29 | `session_id` == `display_code` | Kept on purpose: the code is the gate. The WebSocket, the last path that trusted the id alone, now requires the device id too (#24). |
| 30 | Expired token blocked a valid session guest | `require_host_or_session_member` falls through to the session credential when the token is bad, and keeps both when both are valid. A bad token with nothing to fall back on is still a `401`. |
| 32 | No rate limits on third-party proxies | Per-IP `@limiter.limit` on YouTube search and preview, YouTube Music browse, lyrics provider search and lyrics alignment. |
| 34 | Dead WebSocket code | `ws/sessions.py` (unrouted session join) and the empty `ws/session_state.py` deleted (2026-10-10). |
| 35 | Rate limits saw the nginx container, not the client | `karaoke-network` has a fixed subnet and nginx a pinned address (`172.30.250.10`); `FORWARDED_ALLOW_IPS` trusts only that address, and uvicorn (`>=0.40.0`) reads nginx's `$proxy_add_x_forwarded_for` right to left. Direct callers on `15123` key on their own address. See [Client IPs behind the proxy](/guide#client-ips-behind-the-proxy). |
| 36 | Any account could act inside any session | Queue and roster access let any JWT address any session, and registration and `POST /api/demo/start` hand out JWTs to anyone, so a stranger could skip join-by-code and probe codes unthrottled. `ensure_session_access` now admits only a member device, the hosting account or an admin, with one `403` for a missing or foreign session. `POST /api/sessions` requires a host account. |
| 37 | Public demo accounts held host-wide powers | Demo accounts are hosts, so a visitor could list and cancel every job, read every session's performance history (singer names and join codes) and work lyrics reports. Jobs, lyrics reports, batch-align status and the library audits are admin-only; performance history shows a host only their own sessions. |

---

## Related

- [WebSocket Protocol](websocket-protocol.md) — the WebSocket message catalog
- [Roadmap](roadmap.md) — how these fit into future plans
