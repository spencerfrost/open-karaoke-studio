# WebSocket Architecture Cleanup

## Summary
Cleaned up the WebSocket architecture to follow the proper session-based design with only two main endpoints.

## Changes Made

### Removed Redundant WebSocket Endpoints
**Before:** 7 different WebSocket endpoints
- `/ws/jobs` (global)
- `/ws/performance` (global) ❌ REMOVED
- `/ws/session` (global) ❌ REMOVED  
- `/ws/queue` (global) ❌ REMOVED
- `/ws/session/{session_id}` (session-specific)
- `/ws/session/{session_id}/performance` (session-specific) ❌ REMOVED
- `/ws/session/{session_id}/queue` (session-specific) ❌ REMOVED

**After:** 2 clean endpoints
- `/ws/jobs` (global) ✅ - For background processing jobs
- `/ws/session/{session_id}` (session-specific) ✅ - For all karaoke functionality

### Architecture Benefits

1. **Clear Separation of Concerns**
   - Jobs WebSocket: Global background processing (audio separation, downloads)
   - Session WebSocket: All karaoke session functionality (performance, queue, player state)

2. **Simplified Client Code**
   - Frontend only needs to connect to 2 WebSocket endpoints instead of 7
   - All session-related functionality through one connection reduces complexity

3. **Better Session Isolation**
   - All karaoke functionality is properly scoped to sessions
   - No global state pollution between different karaoke parties

4. **Cleaner API Design**
   - Root endpoint now only advertises the 2 actual endpoints
   - Removed confusing mix of global and session-specific endpoints

### Updated Files

- `backend/fastapi_poc/main.py`:
  - Removed 5 redundant WebSocket endpoint handlers
  - Updated imports to only include needed functions
  - Cleaned up root endpoint documentation
  - Removed obsolete test page routes
  - Updated module docstring

### What Each Endpoint Handles

**`/ws/jobs`** (Global)
```
- Audio processing job updates
- Download progress
- Background task status
```

**`/ws/session/{session_id}`** (Session-Specific)
```
- Performance controls (play, pause, seek, volume)
- Player state synchronization 
- Queue management (add, remove, reorder songs)
- Real-time session updates
```

## Result
Clean, logical WebSocket architecture that matches the session-based karaoke app design. Each endpoint has a clear purpose and scope.