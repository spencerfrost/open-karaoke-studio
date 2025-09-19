# Host Session Persistence Feature

## 🎯 **Core Problem**
Host devices (Stage/SongPlayer pages) lose their session when navigating between pages or refreshing the browser, causing all connected performers to be disconnected and need to rejoin.

## 👥 **Target User Profile**
- **Primary User**: Karaoke session host using computer/tablet connected to TV/projector
- **Context**: Managing karaoke session from main display device
- **Device**: Desktop computer, laptop, or tablet
- **Interaction Pattern**: Create session → Navigate between pages → Return to session seamlessly
- **Authority**: Session owner who controls when session ends

## 🔄 **Current User Journey**
```
1. Host creates session on Stage page (session code: ABCD)
2. Connected performers join and add songs to queue
3. ❌ Host navigates to Library page → Session lost
4. ❌ Host returns to Stage → Must create new session (ABCD2)
5. ❌ All performers disconnected → Must rejoin with new code
```

## ✨ **Desired User Journey**
```
1. Host creates session on Stage page (session code: ABCD)
2. Connected performers join and add songs to queue
3. ✅ Host navigates to Library page → Session persists
4. ✅ Host returns to Stage → Automatically restored to existing session
5. ✅ All performers remain connected → No rejoining needed
6. ✅ Session only ends when host closes entire app
```

## 🏗️ **Technical Solution Overview**

### **Phase 1: Database Enhancement**
- Add `display_name` field to `SessionDevice` table
- Store user's name when they join session
- Enable name persistence within the session
- **Storage Strategy**: Database primary, localStorage cache for performance

### **Phase 2: Client-Side Host Persistence**
- Store host session data in localStorage with unique key
- Persist: `sessionId`, `deviceId`, `isHost` flag, `displayName`
- Survive page navigation but clear on app close/browser close

### **Phase 3: Smart Session Recovery**
- On page load: Check localStorage for existing host session
- Validate session still exists and host is still authorized
- Reconnect WebSocket and restore full session state
- Handle expired/invalid sessions gracefully
- **Recovery includes**: Session data + user's display name from database

### **Phase 4: Host Authority Preservation**
- Host maintains control even after navigation
- Session remains active until explicit host departure
- Performers experience seamless continuity
- Clear visual indicators of session restoration status
- **Name consistency**: Host's name persists across navigation

### **Phase 5: Enhanced Error Handling**
- Network interruption recovery
- Session expiration detection
- Corrupted storage data cleanup
- Graceful fallback to session creation

## 🎨 **UI/UX Changes**

### **Before (Current)**
- Host creates session → Navigation breaks session
- No persistence across page changes
- Performers constantly need to rejoin
- Session lifecycle tied to current page

### **After (Proposed)**
- Host creates session → Navigation preserves session
- Automatic session restoration on page load
- Performers stay connected during host navigation
- Session lifecycle tied to app/browser lifecycle

## 🔒 **Session Lifecycle Management**

### **Host Session States**
- **Creating**: Initial session creation with loading indicator
- **Active**: Normal operation with full functionality
- **Recovering**: Restoring from localStorage with loading indicator
- **Expired**: Session no longer valid, fallback to creation

### **Persistence Triggers**
- **Persist**: When host successfully creates session
- **Restore**: When host returns to session pages
- **Clear**: When host explicitly leaves or app closes

### **Authority Rules**
- **Host Navigation**: Session stays active, performers unaffected
- **Host App Close**: Session ends, all performers disconnected
- **Host Browser Close**: Session ends (localStorage cleared)
- **Network Issues**: Attempt reconnection, show offline state

## 📱 **Host Device Considerations**
- **Page Navigation**: Seamless session preservation
- **Browser Refresh**: Automatic session restoration
- **Tab Switching**: Session remains active
- **Multiple Tabs**: Each tab can restore same session
- **Incognito Mode**: No persistence (expected behavior)

## ⚠️ **Edge Cases & Error Handling**

### **Recovery Scenarios**
- **Valid Session**: Restore successfully, show brief loading
- **Expired Session**: Clear storage, create new session
- **Invalid Session**: Clear storage, create new session
- **Network Failure**: Retry recovery, show error state

### **Storage Management**
- **Corrupted Data**: Detect and clear invalid localStorage
- **Storage Quota**: Minimal data footprint
- **Cross-Origin**: Isolated to karaoke app domain
- **Security**: No sensitive data in localStorage

### **Concurrent Access**
- **Multiple Host Devices**: First valid host maintains control
- **Device Conflicts**: Clear storage for non-host devices
- **Session Takeover**: Prevent unauthorized host changes

## 🎯 **Success Criteria**

### **Host Experience**
- **95% of the time**: Seamless navigation without session loss
- **5% of the time**: Brief loading during session restoration
- **Zero data loss**: Queue and performer connections maintained
- **Intuitive flow**: Navigation feels natural, sessions "just work"

### **Performer Experience**
- **100% of the time**: No disconnection during host navigation
- **Zero rejoining**: Stay connected through host page changes
- **Seamless continuity**: Experience uninterrupted karaoke session
- **Reliable connection**: Trust in session stability

### **Technical Metrics**
- **Recovery Success Rate**: >95% successful restorations
- **Recovery Time**: <2 seconds average restoration time
- **Storage Efficiency**: <1KB per stored session
- **Error Rate**: <5% restoration failures

## 🚀 **Implementation Priority**

### **High Priority (Core Functionality)**
1. **Basic Persistence**: Store/retrieve host session data
2. **Recovery Logic**: Validate and restore existing sessions
3. **Loading States**: Clear UI feedback during restoration
4. **Error Handling**: Graceful failure recovery

### **Medium Priority (Enhanced UX)**
1. **Visual Indicators**: Session status and recovery progress
2. **Network Resilience**: Offline/online state handling
3. **Storage Optimization**: Efficient data management
4. **Cross-Tab Sync**: Multiple tab session coordination

### **Low Priority (Polish)**
1. **Advanced Error Recovery**: Sophisticated retry mechanisms
2. **Performance Monitoring**: Recovery time tracking
3. **Storage Analytics**: Usage and success metrics
4. **Accessibility**: Screen reader support for status messages

## 🔧 **Technical Implementation Details**

### **Storage Schema**
```typescript
interface HostSessionData {
  sessionId: string;
  deviceId: string;
  displayName: string;  // NEW: From database, cached locally
  timestamp: number;    // For expiration checks
}
```

### **Recovery Flow**
```typescript
1. Check localStorage for host session data
2. Validate session exists and is active
3. Verify current device is still the host
4. Restore session state and reconnect WebSocket
5. Update UI with restored session information
6. Handle failures with fallback to creation
```

### **State Management**
```typescript
interface SessionState {
  // Existing state...
  isRecovering: boolean;
  recoveryError: string | null;
  recoverHostSession: () => Promise<void>;
}
```

## 🎯 **Business Impact**

### **User Experience**
- **Reduced Friction**: No more session recreation during navigation
- **Improved Reliability**: Performers stay connected reliably
- **Professional Feel**: App behaves like native karaoke software
- **Time Savings**: Minutes saved per session from rejoining

### **Technical Benefits**
- **Reduced Server Load**: Fewer session creation requests
- **Better WebSocket Management**: Persistent connections maintained
- **Improved Monitoring**: Clear session lifecycle tracking
- **Enhanced Stability**: Fewer connection disruptions

This feature transforms the host experience from a "web page" workflow to a true "application" workflow, where the session feels persistent and reliable like professional karaoke software.