## Feature Summary: Seamless Session Persistence for Mobile Performers

### 🎯 **Core Problem**
Mobile users (performers) get disconnected from karaoke sessions when:
- Refreshing the browser page
- Closing/reopening the app
- Switching between tabs
- Network interruptions

This creates a poor UX where users have to re-enter session codes and names repeatedly.

### 👥 **Target User Profile**
- **Primary User**: Audience members using mobile phones
- **Context**: Sitting in audience waiting to perform
- **Device**: Mobile phone/tablet
- **Interaction Pattern**: Join session once → Add songs to queue as needed → Stay connected until session ends
- **Session Authority**: Host computer (connected to TV) controls session lifecycle

### 🔄 **Current User Journey**
```
1. Open app on phone
2. Enter 4-character session code (ABCD)
3. Enter performer name (John Doe)
4. Add songs to queue when ready
5. ❌ Page refresh → Disconnected → Repeat steps 2-3
```

### ✨ **Desired User Journey**
```
1. Open app on phone
2. Enter 4-character session code (ABCD) 
3. Enter performer name (John Doe)
4. ✅ Add songs to queue as needed
5. ✅ Page refresh → Automatically reconnected
6. ✅ Stay connected until host ends session
```

### 🏗️ **Technical Solution Overview**

#### **Phase 1: Database Enhancement**
- Add `display_name` field to `SessionDevice` table
- Store user's name when they join session
- Enable name persistence within the session
- **Storage Strategy**: Database primary, localStorage cache for performance

#### **Phase 2: Client-Side Persistence** 
- Store session credentials in localStorage
- Include: `sessionId`, `displayCode`, `deviceId`, `displayName`
- Enable automatic session restoration on page load

#### **Phase 3: Smart Session Recovery**
- On app startup: Check localStorage for valid session
- Attempt to rejoin stored session automatically
- If successful: User continues seamlessly with stored name
- If failed: Clear stored data, show normal join flow

#### **Phase 4: UI Simplification**
- Replace complex AddToQueueDialog with simple JoinSessionDialog
- Remove manual session joining from pages that require sessions
- Replace with loading states during session restoration
- Keep manual join flow as fallback for new users or failed restorations

### 🎨 **UI/UX Changes**

#### **Before (Current)**
- Every session-required page has its own join UI
- Users re-enter code + name on every page load
- Complex conditional rendering based on session state
- AddToQueueDialog shows even when user is already in session

#### **After (Proposed)**
- Session restoration happens automatically on app load
- Pages show loading spinner during restoration
- Manual join UI only appears for new users or failed restorations
- User's name is remembered for the entire session
- **JoinSessionDialog**: Single, reusable dialog for session joining
- **No dialogs**: When user is already in session, actions happen instantly

### 🔒 **Session Lifecycle Clarification**
- **Session Start**: When host creates session
- **Session End**: When host leaves/closes app (not individual performers)
- **Performer Lifecycle**: Join once → Stay connected → Leave when session ends
- **Persistence Scope**: Per device, per session (not cross-device or permanent)
- **Name Storage**: Database primary (authoritative), localStorage cache (performance)

### 📱 **Mobile-First Considerations**
- **Network Resilience**: Handle offline/online transitions gracefully
- **Battery Optimization**: Minimize background activity
- **Touch Interactions**: Optimize for mobile touch patterns
- **Memory Constraints**: Keep localStorage usage minimal

### ⚠️ **Edge Cases & Error Handling**
- **Expired Sessions**: Clear localStorage when session no longer exists
- **Host Disconnection**: Handle when host leaves unexpectedly
- **Device Conflicts**: Handle if same user joins from multiple devices
- **Network Issues**: Graceful degradation when offline
- **Storage Corruption**: Handle corrupted localStorage data
- **Failed Auto-Recovery**: Show JoinSessionDialog as fallback
- **Failed Manual Join**: Show error message, don't keep dialog open

### 🎯 **Success Criteria**
- **95% of the time**: Seamless experience - refresh page, continue performing
- **5% of the time**: Brief loading, then normal join flow
- **Zero data loss**: User's queue position and preferences maintained
- **Intuitive flow**: Users don't need to understand "sessions" - it just works
- **Name persistence**: User's name survives page refreshes and reconnections

### 🚀 **Implementation Priority**

#### **Phase 1: Core Infrastructure (Current Sprint)**
1. **Database Schema**: Add `display_name` to `SessionDevice` table
2. **Backend APIs**: Update join endpoints to accept/store names
3. **JoinSessionDialog**: Create reusable session joining component
4. **UI Simplification**: Remove AddToQueueDialog complexity

#### **Phase 2: Session Persistence (Next Sprint)**
1. **Client Persistence**: Implement localStorage caching
2. **Auto-Recovery**: Smart session restoration logic
3. **Loading States**: Clear UI feedback during restoration
4. **Error Handling**: Graceful failure recovery

#### **Phase 3: Polish & Optimization (Future)**
1. **Network Resilience**: Offline/online state handling
2. **Cross-Tab Sync**: Multiple tab session coordination
3. **Performance Monitoring**: Recovery time tracking
4. **Advanced Error Recovery**: Sophisticated retry mechanisms

### 🔧 **Technical Implementation Details**

#### **Storage Schema**
```typescript
// Database (Primary - Authoritative)
interface SessionDevice {
  // ... existing fields
  display_name: string | null;  // NEW: User's name in session
}

// localStorage (Cache - Performance)
interface StoredSession {
  sessionId: string;
  deviceId: string;
  displayName: string;  // From database, cached locally
  timestamp: number;    // For expiration checks
}
```

#### **Recovery Flow**
```typescript
1. Check localStorage for session data
2. Validate session exists and is active
3. Verify stored name matches database (optional consistency check)
4. Restore session state and reconnect WebSocket
5. Update UI with restored session information
6. Handle failures with fallback to JoinSessionDialog
```

#### **UI Component Architecture**
```typescript
// New simplified architecture
JoinSessionDialog    // Single reusable join dialog
  ↓
SessionStore        // Manages session state + persistence
  ↓  
SongCard           // Simple component, no dialog logic
```

#### **Error Handling Strategy**
```typescript
// Auto-recovery failures → Show join dialog
try {
  await recoverSession();
} catch (error) {
  clearStoredSession();
  showJoinSessionDialog();
}

// Manual join failures → Show error, keep dialog closed
try {
  await joinSession(code, name);
} catch (error) {
  showToast("Failed to join session. Please try again.");
}
```

### 🎯 **Business Impact**

#### **User Experience**
- **Reduced Friction**: No more session recreation during navigation
- **Improved Reliability**: Performers stay connected reliably
- **Professional Feel**: App behaves like native karaoke software
- **Time Savings**: Minutes saved per session from rejoining
- **Name Memory**: Users enter name once, never again

#### **Technical Benefits**
- **Reduced Server Load**: Fewer session creation requests
- **Better WebSocket Management**: Persistent connections maintained
- **Improved Monitoring**: Clear session lifecycle tracking
- **Enhanced Stability**: Fewer connection disruptions
- **Simplified UI**: Cleaner component architecture

This feature transforms the app from a "web page" experience to a true "mobile app" experience for performers, where the session feels persistent and reliable like a native karaoke app.