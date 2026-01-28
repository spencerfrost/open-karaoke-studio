# Open Karaoke Studio - Roadmap

Brain dump of ideas, improvements, and future work organized by theme. This is an evolving document - priorities and ideas will change over time.

---

## Current State

### What's Working Well ✅

- **Complete Feature Set:** All 24 major features are fully functional
- **Session Isolation:** Proper session-based state management keeps multi-user sessions separate
- **Real-Time Sync:** WebSocket architecture keeps all devices synchronized
- **Background Processing:** Celery handles long-running audio jobs without blocking UI
- **Multiple Separation Engines:** Demucs, Roformer, and Hybrid options for audio quality
- **Comprehensive Backend Tests:** 2,277 test files ensure backend reliability

### Known Pain Points 😓

- **No Frontend Tests:** Zero test coverage for UI components
- **Logging Issues:** Console.log and print() statements instead of proper logging
- **Session State Bugs:** Global performance state violates session isolation
- **Resource Management:** Job cancellation UI exists but doesn't actually cancel jobs
- **Type Safety Gaps:** Some `as any` type bypasses in frontend code

---

## Critical Fixes

These should be addressed ASAP to improve stability and correctness.

### 1. Implement Celery Job Cancellation
**Problem:** Cancel button in UI doesn't actually stop Celery tasks

**Impact:** Wastes CPU/GPU resources running unwanted audio processing jobs

**Solution:**
```python
from celery import current_app
current_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
```

**Effort:** Small (1-2 hours)

---

### 2. Replace Print Statements with Logging
**Problem:** 6 WebSocket files use `print()` instead of `logging` module

**Files:**
- backend/app/ws/session_specific.py
- backend/app/ws/sessions.py
- backend/app/ws/connection_manager.py
- backend/app/ws/queue.py
- backend/app/ws/jobs.py

**Impact:** Can't debug production issues, logs are invisible in Celery

**Solution:** Replace all print() with logger.info/debug/error

**Effort:** Small (1-2 hours)

---

### 3. Remove Console.log Spam
**Problem:** 50+ console.log statements across frontend

**Impact:** Production performance overhead, cluttered console, potential data leaks

**Solution:**
- Add proper logging library (loglevel, pino)
- Add debug environment variable
- Remove or guard console statements in production

**Effort:** Medium (2-3 hours)

---

### 5. Fix Type Safety Issues
**Problem:** Type bypasses with `as any` in frontend

**Impact:** Runtime errors possible, TypeScript benefits lost

**Solution:** Define proper interfaces, remove type bypasses

**Effort:** Small (1 hour)

---

## Quality & Testing

### Frontend Test Infrastructure
**Status:** 🚧 Not started

**Problem:** Zero test coverage for React components, hooks, stores

**Impact:** Risky refactoring, no quality assurance for UI

**Plan:**
1. Set up Vitest or Jest + React Testing Library
2. Start with critical paths:
   - Player component and hooks
   - Queue management
   - Session connection logic
3. Add test coverage to CI/CD pipeline
4. Aim for 70%+ coverage of critical paths

**Effort:** Large (1-2 days initial setup, ongoing)

---

### Centralized Error Handling
**Status:** 🚧 Improvement needed

**Current State:** Try/catch blocks with console.error() scattered throughout

**Plan:**
- Implement React error boundaries
- Add error tracking (Sentry, LogRocket, etc.)
- Show user-friendly error messages
- Centralized error logging service

**Effort:** Medium (4-6 hours)

---

### ESLint Warning Cleanup
**Status:** 🚧 Technical debt

**Problem:** 9 locations with `eslint-disable` comments, mostly `react-hooks/exhaustive-deps`

**Plan:**
- Review each case
- Fix dependency arrays properly
- Only disable if absolutely necessary
- Document why disables are needed

**Effort:** Small (2-3 hours)

---

## Missing Features

### Queue Drag-and-Drop Reordering
**Status:** 📋 Planned (TODO in code)

**User Story:** As a user, I want to reorder the queue by dragging songs

**Implementation:**
- Use react-beautiful-dnd or @dnd-kit
- Add drag handles to queue items
- Update backend API endpoint
- Broadcast reorder to all session devices

**Effort:** Medium (4-6 hours)

---

### Song Preloading
**Status:** 📋 Incomplete (TODO in code)

**User Story:** As a user, I want seamless transitions between songs

**Current:** Preload hook exists but logic not implemented

**Implementation:**
- Preload audio for next song in queue
- Use Web Audio API to buffer next track
- Start loading when 80% through current song
- Reduce gap between songs to near-zero

**Effort:** Medium (3-4 hours)

---

### Settings Page
**Status:** 🚧 Partially exists

**User Story:** As a user, I want to configure default settings

**Current:** Settings page exists but mostly empty

**Needed Settings:**
- Default singer name (currently hardcoded as "global")
- Audio quality preferences
- Separation engine default
- Lyrics display preferences
- UI theme/color preferences

**Effort:** Medium (6-8 hours for full implementation)

---

### Queue Item Thumbnails
**Status:** 📋 Planned (TODO in code)

**User Story:** As a user, I want to see artwork in the queue

**Current:** TODO comment exists, feature "being finalized"

**Implementation:**
- Add artwork thumbnail to queue item display
- Handle missing artwork gracefully
- Optimize image loading

**Effort:** Small (1-2 hours)

---

### QR Code Session Joining
**Status:** 🚧 Component exists, not prominently used

**User Story:** As a user, I want to join sessions by scanning QR code

**Current:** QRCodeDisplay component exists but not actively shown

**Implementation:**
- Add QR code to session info display
- Show on stage view
- Make prominent in join flow
- Test with mobile devices

**Effort:** Small (2-3 hours)

---

## Performance Improvements

### Optimistic UI Updates for Songs
**Status:** 📋 Planned (TODO in code)

**User Story:** As a user, I want instant feedback when I perform actions

**Current:** Disabled due to complex query key structure

**Implementation:**
- Simplify TanStack Query key structure
- Add optimistic updates for:
  - Adding songs to queue
  - Deleting songs
  - Updating metadata
- Better perceived performance

**Effort:** Medium (4-6 hours)

---

### WebSocket Connection State Improvements
**Status:** 🚧 Missing 'connecting' state

**Problem:** Player shows only connected/disconnected, no connecting state

**Implementation:**
- Add 'connecting' state detection
- Show loading spinner during connection
- Better UX for connection issues
- Timeout handling

**Effort:** Small (1-2 hours)

---

### Download Progress Feedback
**Status:** 📋 Missing

**Problem:** No progress feedback during YouTube download phase

**Implementation:**
- Add progress callback to yt-dlp
- Broadcast download progress via WebSocket
- Show download % in jobs queue
- ETA calculation

**Effort:** Medium (3-4 hours)

---

## Architecture Improvements

### Player Store State Management
**Status:** 🚧 Has workarounds

**Problem:** Store reset causes infinite loops, workaround in place

**Quote from code:**
> "We don't reset the store state here as it causes infinite loops"

**Investigation Needed:**
- Root cause of infinite loop
- Proper store lifecycle management
- Fix architecture vs working around it

**Effort:** Medium-Large (4-8 hours investigation + fix)

---

### WebSocket Cleanup Management
**Status:** 🚧 Uses global window object

**Current:** Cleanup callbacks stored in `window.__playerWebSocketCleanup`

**Improvement:**
- Use refs or context for cleanup
- More idiomatic React patterns
- Avoid polluting global namespace

**Effort:** Small-Medium (2-4 hours)

---

### Database Schema Evolution: Lyrics Metadata
**Status:** 📋 Planned

**Current State:** Lyrics and their metadata (plain, synced, duration, etc.) are stored directly on the song record

**Proposed Change:**
- Move lyrics to a dedicated table, linked to songs
- Store additional metadata: type (plain/synced), duration, alignment info, vocal onset timestamp, etc.
- This enables more flexible data management and future features
- Supports multiple lyrics versions per song (different ASR models, manual edits, etc.)

**Benefits:**
- More normalized data structure
- Better support for AI-generated lyric variations
- Improved query performance for lyric searches
- Easier to track alignment metadata

**Effort:** Medium (6-8 hours for migration + testing)

---

### Migration System Cleanup
**Status:** 🚧 Has workarounds

**Problem:** Migration checks if column exists (indicates manual fixes)

**Tasks:**
- Review migration history
- Ensure migrations are idempotent
- Document any manual changes
- Clean up workarounds

**Effort:** Medium (3-5 hours)

---

## Future Ideas

### Audio Processing

**Pitch Shifting & Key Transposition**
- Real-time pitch shifting for singers
- Transpose up/down by semitones
- Save preferred key per song
- Preserve audio quality (use high-quality algorithms like PSOLA or phase-vocoder)

**Advanced Audio Processing**
- Formant preservation during pitch shifting
- Real-time audio effects chains
- Time-stretching without pitch changes
- Vocal isolation improvements

**Echo/Reverb Effects**
- Vocal effects (echo, reverb, chorus)
- Effect presets (studio, concert hall, etc.)
- Per-session effect settings

**Audio Normalization**
- Normalize volume across songs
- Prevent loud/quiet song transitions
- ReplayGain integration

**Vocal Onset Detection**
- Use Python audio analysis libraries (e.g., `librosa`, `madmom`) to detect onsets in the vocal track
- Focus on energy spikes or spectral changes that indicate the start of singing
- Speech-to-Text with Timestamps: Use models like OpenAI Whisper, Vosk, or other ASR tools to transcribe the vocal track and obtain word-level timestamps
- Distinguish between non-word sounds (intros, breaths) and actual lyrics
- Enable more precise alignment and advanced features like bouncing ball karaoke

---

### Lyrics Features

**Aligning Synced Lyrics with Vocal Start**
- **Goal:** Precisely align the start of synced lyrics with the true start of vocals in each song's isolated vocal track.
- **Motivation:** Sometimes, vocal tracks contain non-word intros (e.g., ooo, ahhh) or non-vocal sounds that are picked up by AI separation. The true start of the main vocal is not always at the beginning of the track.
- **Approach Ideas:**
  - Analyze the vocal track to detect the first significant vocal onset (ideally, the first word sung)
  - Use this to align or shift the synced lyrics, or crop the vocal track for better alignment
  - Compare the duration of the synced lyrics with the audio to estimate a window for onset detection (e.g., check within a 3-6 second window)

**Synced Lyrics Enhancements (AI-Generated Karaoke)**
- Explore STT (Speech-to-Text) models that can generate synced lyrics from vocal tracks
- Use aligned vocal tracks and synced lyrics as training data for models that can generate synced lyrics from new vocal tracks
- Explore bouncing ball karaoke by generating word-level or syllable-level timing
- Potentially train custom models for even more precise lyric alignment and karaoke effects

**Lyrics Editor**
- In-app LRC timestamp editor
- Click to set timestamps while playing
- Bulk offset adjustment
- Preview while editing

**Lyrics Import/Export**
- Import LRC files directly
- Export edited lyrics
- Share lyrics between users

**Multi-Language Lyrics**
- Support for multiple language tracks
- Toggle between languages
- Romaji support for Japanese songs

---

### Library Management

**Playlists**
- Create custom playlists
- Share playlists with session
- Auto-queue entire playlist
- Smart playlists (recently added, most played, etc.)

**Song Ratings & History**
- Rate songs (1-5 stars)
- Track play history
- "Most popular" sorting
- Personal favorites list

**Batch Operations**
- Bulk metadata editing
- Bulk reprocessing with different engine
- Bulk delete
- Bulk artwork update

**Advanced Search**
- Filter by BPM range
- Filter by genre
- Filter by year/decade
- Saved searches

---

### Session Features

**Session History**
- View past sessions
- See what was played
- Replay past session queues
- Session statistics

**User Accounts**
- Optional user accounts
- Save preferences per user
- User-specific libraries
- User statistics (songs sung, favorites)

**Voting System**
- Upvote songs in queue
- Democratic queue ordering
- Host can enable/disable voting
- Voting affects queue order

**Session Templates**
- Save session configurations
- Quick start with template
- Preset performance settings
- Default queue songs

---

### Mobile App

**Native Mobile Apps**
- iOS/Android native apps
- Better mobile performance
- Offline capability
- Push notifications for queue position

**Mobile-Optimized UI**
- Dedicated mobile layouts
- Touch-optimized controls
- Swipe gestures
- Better mobile performance controls

---

### Social Features

**Song Requests**
- Public URL for song requests
- Request moderation by host
- Request queue separate from main queue
- Requester name display

**Leaderboards**
- Most songs sung
- Most songs added
- Session participation stats
- Weekly/monthly/all-time

---

### Admin Features

**Usage Analytics**
- Track song popularity
- Session statistics
- Processing job stats
- Storage usage monitoring

**System Health Dashboard**
- Celery worker status
- WebSocket connection count
- Database size
- CPU/GPU usage
- Error rate monitoring

**Backup & Restore**
- Database backup/restore
- Library export/import
- Configuration export/import
- Automated backups

---

## Experimental Code Cleanup

**Status:** 🧪 Experimental code in production repo

**Locations:**
- `/backend/scripts/bpm_investigation/` - 8 BPM detection strategies
- `/backend/scripts/ai_lyrics/asr_experiments/` - ASR experiments
- `/backend/app/services/separation_engines/` - Multiple engines

**Options:**
1. Move experiments to separate branch
2. Clearly mark as experimental in README
3. Document which components are production-ready
4. Delete if no longer needed

**Effort:** Small (1-2 hours documentation)

---

## Documentation

**Completed:**
- ✅ FEATURES.md - Complete feature inventory
- ✅ TECH-DEBT.md - Prioritized issues
- ✅ ROADMAP.md - This document
- ✅ ARCHITECTURE.md - Technical deep-dive
- ✅ CLAUDE.md - AI assistant context

**Future docs/ Topics:**
- WebSocket Protocol Guide
- Audio Processing Deep-Dive
- Session Lifecycle Diagrams
- Deployment Guide
- Contribution Guide (if opening to contributors)
- API Reference

---

## Notes

- This is a **living document** - add ideas as they come up
- No strict timeline - priorities will shift
- Focus on **quick wins** when time is limited
- **Quality over quantity** - better to do fewer things well
- Get **critical fixes** done before adding features
- **Test coverage** is important but don't let it block progress

---

## How to Use This Roadmap

1. **Feeling Lost?**
   - Read "Current State" to remember what's working
   - Check "Critical Fixes" for high-priority work

2. **Need Something to Work On?**
   - Start with "Critical Fixes" (highest impact)
   - Then "Quality & Testing" (long-term investment)
   - Then "Missing Features" (user-visible improvements)

3. **Have a New Idea?**
   - Add it to the appropriate section
   - Don't worry about priority yet
   - Just capture it so you don't forget

4. **Reviewing Progress?**
   - Update status indicators (📋 🚧 ✅)
   - Move completed items to notes
   - Adjust priorities based on learnings

---

**Last Updated:** 2026-01-28
