# Session-Based WebSocket Architecture for Party Mode

## Overview
This document outlines the design and implementation plan for a session-based WebSocket architecture to solve connectivity and synchronization issues in Open Karaoke Studio's party mode. The current system has multiple disconnected WebSocket implementations that don't guarantee devices are connected to the same session, leading to sync issues and unreliable performance controls.

## Problem Statement

### Current Issues
1. **Multiple Disconnected WebSocket Systems**: Jobs, performance controls, and queue WebSockets operate independently
2. **No Session Management**: All clients auto-connect to global rooms without explicit session joining
3. **Connection Reliability**: Devices often fail to connect properly or lose sync
4. **Performance Controls Not Syncing**: Backend exists but frontend integration is incomplete
5. **No Multi-Party Support**: Cannot run multiple karaoke setups simultaneously

### Current WebSocket Architecture
- **Jobs WebSocket**: Works well for file processing (✅)
- **Performance Controls**: Backend exists but frontend integration incomplete (❌)
- **Karaoke Queue**: Uses hardcoded global room, no session isolation (⚠️)

## Proposed Solution: Session-Based WebSocket Architecture

### Core Concept
- **Stage device** creates a karaoke session with unique session ID
- **4-character code** displayed on stage for easy joining
- **Other devices** join the session using code entry at `/join`
- **All WebSocket communications** are routed through session-specific rooms
- **Real-time sync** guaranteed for all devices in the same session

### Key Benefits
1. **Explicit Session Management**: Clear session creation and joining process
2. **Guaranteed Synchronization**: All devices in same session connect to same WebSocket rooms
3. **Better UX**: Visual confirmation that devices are connected correctly
4. **Session Isolation**: Multiple karaoke setups can run simultaneously
5. **Connection Reliability**: Structured approach to WebSocket connectivity

## Technical Architecture

### Data Models

#### Session Model
```typescript
interface KaraokeSession {
  sessionId: string;           // Unique session identifier
  displayCode: string;         // 4-character code for manual entry
  hostDeviceId: string;        // Socket ID of the stage device
  createdAt: string;           // Session creation timestamp
  connectedDevices: ConnectedDevice[];
  isActive: boolean;           // Session status
  expiresAt: string;           // Auto-cleanup timestamp
}

interface ConnectedDevice {
  deviceId: string;            // Socket ID
  deviceType: 'stage' | 'performer' | 'controller';
  joinedAt: string;
  isActive: boolean;
  userAgent?: string;          // For device identification
}
```

#### Session Room Naming Convention
- Main session room: `session_{sessionId}`
- Performance controls: `session_{sessionId}_controls`
- Queue updates: `session_{sessionId}_queue`
- Job updates: `session_{sessionId}_jobs`

### Backend Implementation

#### Session WebSocket Handler (`backend/app/websockets/session_ws.py`)
```python
# Core session management WebSocket events
- create_session
- join_session_by_id
- join_session_by_code
- leave_session
- disconnect_from_session
- get_session_info
- list_connected_devices

# Session room management
- Auto-join devices to session-specific rooms
- Route existing WebSocket events through session context
- Handle device disconnection/reconnection
- Session cleanup and expiration
```

#### Updated WebSocket Handlers
- **Performance Controls**: Route through session rooms instead of global
- **Karaoke Queue**: Use session-specific queue rooms
- **Jobs**: Optionally route job updates through session context

#### Database Schema
```sql
-- New table for session management
CREATE TABLE karaoke_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(32) UNIQUE NOT NULL,
    display_code VARCHAR(4) UNIQUE NOT NULL,
    host_device_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE session_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(32) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    device_type VARCHAR(20) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    user_agent TEXT,
    FOREIGN KEY (session_id) REFERENCES karaoke_sessions(session_id)
);
```

### Frontend Implementation

#### Session Management Store (`frontend/src/stores/sessionStore.ts`)
```typescript
// Zustand store for session state management
interface SessionState {
  sessionId: string | null;
  displayCode: string | null;
  connectedDevices: ConnectedDevice[];
  isHost: boolean;
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

// Actions
- createSession()
- joinSession(sessionIdOrCode: string)
- leaveSession()
- getSessionInfo()
- refreshConnectedDevices()
```

#### Updated Components

##### Stage Component Enhancement
```typescript
// Display session info at top of stage
- 4-character display code
- Connected device count
- Session status indicator

// Auto-create session on stage load
// Handle session reconnection logic
```

##### New Join Session Page (`/join` and `/join/:sessionId`)
```typescript
// Simple joining method:
- Manual 4-character code entry

// Features:
- Session validation
- Device type selection (performer/controller)
- Connection status feedback
- Redirect to appropriate interface after joining
```

##### Library Page Updates
```typescript
// Add session context to "Add to Queue" actions
// Show session status in header
// Handle queue updates through session WebSocket
```

#### WebSocket Service Updates
```typescript
// Enhanced WebSocket service with session awareness
- Auto-join session rooms on connection
- Handle session-specific event routing
- Reconnection logic with session restoration
- Connection status management
```

## Implementation Plan

### Phase 1: Core Session Infrastructure (Week 1)
**Backend Tasks:**
- [ ] Create session WebSocket handler (`session_ws.py`)
- [ ] Add database schema for sessions and devices
- [ ] Implement session creation and joining logic
- [ ] Add session cleanup/expiration background task

**Frontend Tasks:**
- [ ] Create session management store (`sessionStore.ts`)
- [ ] Create join session page (`/join`)
- [ ] Basic session UI components

**Testing:**
- [ ] Unit tests for session creation/joining
- [ ] Integration tests for WebSocket session events

### Phase 2: Integrate Existing WebSockets (Week 2)
**Backend Tasks:**
- [ ] Update performance controls WebSocket to use session rooms
- [ ] Update karaoke queue WebSocket to use session rooms
- [ ] Update jobs WebSocket to optionally use session context
- [ ] Add session validation to all WebSocket handlers

**Frontend Tasks:**
- [ ] Update Stage component with session UI
- [ ] Integrate session context into existing WebSocket services
- [ ] Update Library page with session-aware queue actions
- [ ] Add session status indicators throughout app

**Testing:**
- [ ] End-to-end tests for multi-device session scenarios
- [ ] Performance controls sync testing
- [ ] Queue synchronization testing

### Phase 3: Enhanced Features & Polish (Week 3)
**Backend Tasks:**
- [ ] Device type identification and role-based features
- [ ] Session persistence across server restarts
- [ ] Advanced session management (transfer host, kick devices)
- [ ] Analytics and session monitoring

**Frontend Tasks:**
- [ ] Enhanced session management UI
- [ ] Device type-specific interfaces
- [ ] Session reconnection UX improvements
- [ ] Error handling and user feedback

**Testing:**
- [ ] Load testing with multiple simultaneous sessions
- [ ] Edge case testing (network issues, server restarts)
- [ ] User acceptance testing

### Phase 4: Advanced Features (Future)
- [ ] Session passwords/private sessions
- [ ] Voice chat integration through session rooms
- [ ] Session recording and playback
- [ ] Advanced device management and permissions
- [ ] Session templates and presets

## Technical Considerations

### Session Management
- **Session Expiration**: Auto-cleanup inactive sessions after configurable timeout
- **Reconnection Handling**: Devices can rejoin existing sessions after disconnection
- **Host Transfer**: Support transferring session host to another device
- **Session Persistence**: Store session state in database for server restart recovery

### Security & Validation
- **Session ID Generation**: Use cryptographically secure random session IDs
- **Display Code Uniqueness**: Ensure 4-character codes are unique across active sessions
- **Rate Limiting**: Prevent session creation/joining abuse
- **Input Validation**: Validate all session-related inputs

### Performance & Scalability
- **Room Management**: Efficient WebSocket room join/leave operations
- **Memory Usage**: Monitor session and device object memory consumption
- **Concurrent Sessions**: Support multiple simultaneous karaoke sessions
- **Database Indexing**: Proper indexing on session_id and display_code

### Error Handling
- **Connection Failures**: Graceful handling of WebSocket connection issues
- **Session Not Found**: Clear error messages for invalid session codes
- **Host Disconnection**: Handle stage device disconnection scenarios
- **Network Recovery**: Auto-reconnection with session restoration

## Success Criteria

### Functional Requirements
- [x] Stage device can create a session with 4-character code
- [x] Other devices can join session via code entry
- [x] All devices in session receive synchronized WebSocket updates
- [x] Performance controls sync properly across devices
- [x] Queue actions are reflected on all devices in real-time
- [x] Multiple sessions can run simultaneously without interference

### Non-Functional Requirements
- [x] Session creation and joining completes within 2 seconds
- [x] WebSocket events propagate to all session devices within 100ms
- [x] System supports at least 10 concurrent sessions
- [x] Each session supports at least 20 connected devices
- [x] 99.9% uptime for session WebSocket connections

### User Experience
- [x] Clear visual indication of session connection status
- [x] Intuitive manual code joining process
- [x] Immediate feedback for all session actions
- [x] Graceful handling of connection issues with user notification
- [x] No more than 3 steps to join a session from any device

## Dependencies

### New Dependencies
- **None for initial implementation** (QR codes moved to future enhancement)

### Existing Dependencies
- **Socket.IO**: Already in use, will extend for session management
- **Zustand**: Already in use for state management
- **SQLite/Database**: Already in use, will add session tables

## Risks & Mitigation

### Technical Risks
- **WebSocket Connection Stability**: Implement robust reconnection logic
- **Session State Consistency**: Use database as source of truth
- **Memory Leaks**: Implement proper cleanup for expired sessions
- **Concurrent Access**: Use proper locking for session operations

### UX Risks
- **Simple Join Process**: 4-character code is easy to communicate verbally
- **Connection Confusion**: Clear status indicators and error messages
- **Device Compatibility**: No special hardware requirements (camera for QR scanning)

## Future Enhancements

### Short Term
- **QR code integration** for easier joining (scan to join)
- Session passwords for private sessions
- Advanced device roles and permissions
- Session history and analytics

### Long Term
- Voice chat integration
- Multi-room/lobby system
- Advanced session management dashboard
- API for third-party integrations

---

This document serves as the comprehensive specification for implementing session-based WebSocket architecture in Open Karaoke Studio. Implementation should follow the phased approach outlined above, with regular testing and validation at each phase.
