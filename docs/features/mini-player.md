# In-App Mini-Player Feature

## 🎯 Overview

This document outlines the design and implementation plan for an **in-app floating mini-player** that allows users to navigate away from the player page while a song continues playing. This is similar to YouTube's mini-player that appears in the corner when you browse away from a video - entirely within our web application, not the browser's native Picture-in-Picture window.

### Use Case

When a karaoke performance is finishing (e.g., during a long outro after the performer is done singing), the host or performer may want to:
- Browse the library for the next song
- Check the queue
- Adjust settings

Rather than staying stuck on the player page, they can navigate freely while the mini-player keeps the song visible and controllable in a corner of the screen.

---

## 🔬 Research Summary

### Approach Options Analyzed

#### Option 1: Browser Native Picture-in-Picture API ❌
**Not Recommended for Our Use Case**

The browser's native PiP API (`HTMLVideoElement.requestPictureInPicture()`) creates a floating window that sits **outside** the browser. While powerful, it has limitations:

- **Pros**: Always-on-top even when switching apps, native browser controls
- **Cons**: 
  - Opens a separate OS-level window (not "in-app")
  - Limited customization of controls
  - Firefox has no support
  - Doesn't integrate with our app's UI/theme
  - User loses the "in-app" experience

#### Option 2: Document Picture-in-Picture API ❌
**Not Recommended - Limited Browser Support**

A newer API (`window.documentPictureInPicture.requestWindow()`) that allows arbitrary HTML content in a PiP window.

- **Pros**: Can render any content, more flexible than video-only PiP
- **Cons**:
  - **Very limited browser support** (Chrome 116+, no Firefox, no Safari)
  - Still creates a separate window outside the app
  - Experimental/unstable API

#### Option 3: React Portal-Based In-App Mini-Player ✅
**Recommended Approach**

Create a mini-player component that renders at the app root level using React Portals, persisting across navigation.

- **Pros**:
  - Fully in-app experience (like YouTube's mini-player)
  - Complete control over styling and behavior
  - Works in all browsers
  - Integrates with our Zustand state management
  - Can show lyrics, controls, visualizer - whatever we want
  - Draggable, resizable, fully customizable
- **Cons**:
  - More implementation effort
  - Need to handle z-index and layout carefully

---

## 🏗️ Recommended Architecture

### Core Concept

The mini-player is a **persistent UI element** rendered at the `App.tsx` level (outside of React Router routes). It:
1. Shows when playback is active AND user navigates away from the player page
2. Hides when user returns to the player page
3. Maintains the same Zustand store state as the main player
4. Allows basic controls (play/pause, volume, expand back to full player)

### State Management

Since we already use `useKaraokePlayerStore` (Zustand) for player state, the mini-player can simply consume the same store. No additional state sync needed!

```
┌─────────────────────────────────────────────────────────────────┐
│  App.tsx                                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Router / Routes                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Page Components (Library, Stage, Settings, etc.)   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  <MiniPlayer /> (Portal to body, fixed position)          │  │
│  │  - Conditionally rendered based on playback state         │  │
│  │  - Consumes useKaraokePlayerStore                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
frontend/src/
├── components/
│   └── player/
│       └── MiniPlayer/
│           ├── index.ts                 # Clean exports
│           ├── MiniPlayer.tsx           # Main component
│           ├── MiniPlayer.types.ts      # TypeScript interfaces
│           ├── MiniPlayerControls.tsx   # Play/pause, expand button
│           ├── MiniPlayerProgress.tsx   # Small progress indicator
│           └── useMiniPlayer.ts         # Logic hook
├── stores/
│   └── useKaraokePlayerStore.ts         # (existing) - add mini-player visibility state
└── App.tsx                              # Add MiniPlayer render
```

---

## 📋 Detailed Implementation Plan

### Phase 1: Store Enhancement (0.5 day)

Add mini-player visibility state to the existing Zustand store.

```typescript
// useKaraokePlayerStore.ts additions
interface KaraokePlayerState {
  // ... existing state ...
  
  // Mini-player state
  miniPlayerEnabled: boolean;        // User preference (show mini-player when navigating away)
  miniPlayerPosition: { x: number; y: number }; // Persist position if draggable
  
  // Derived/computed
  shouldShowMiniPlayer: () => boolean;  // True when playing AND not on player page
  
  // Actions
  setMiniPlayerEnabled: (enabled: boolean) => void;
  setMiniPlayerPosition: (position: { x: number; y: number }) => void;
}
```

### Phase 2: Route Detection Hook (0.5 day)

Create a hook to detect if we're on a player-related page.

```typescript
// hooks/useIsPlayerPage.ts
import { useLocation } from 'react-router-dom';

export function useIsPlayerPage(): boolean {
  const location = useLocation();
  
  // Player-related routes where mini-player should NOT show
  const playerRoutes = [
    '/player/',      // Direct song player
    '/stage',        // Stage view (full player experience)
  ];
  
  return playerRoutes.some(route => location.pathname.startsWith(route));
}
```

### Phase 3: MiniPlayer Component (2-3 days)

#### Main Component

```typescript
// MiniPlayer.tsx
import React from 'react';
import { createPortal } from 'react-dom';
import { useKaraokePlayerStore } from '@/stores/useKaraokePlayerStore';
import { useIsPlayerPage } from '@/hooks/useIsPlayerPage';
import { useMiniPlayer } from './useMiniPlayer';
import MiniPlayerControls from './MiniPlayerControls';
import MiniPlayerProgress from './MiniPlayerProgress';

const MiniPlayer: React.FC = () => {
  const { isPlaying, songId, currentTime, duration } = useKaraokePlayerStore();
  const isPlayerPage = useIsPlayerPage();
  const { position, handleDrag, expand, close } = useMiniPlayer();
  
  // Only show when: playing, has a song, and NOT on a player page
  const shouldShow = isPlaying && songId && !isPlayerPage;
  
  if (!shouldShow) return null;
  
  return createPortal(
    <div 
      className="fixed z-50 shadow-2xl rounded-lg overflow-hidden bg-background border border-border"
      style={{
        bottom: position.y,
        right: position.x,
        width: '320px',
        height: '180px',
      }}
    >
      {/* Song info and mini lyrics/visualizer */}
      <div className="relative w-full h-full">
        {/* Mini visualizer or album art background */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
        
        {/* Content overlay */}
        <div className="absolute inset-0 flex flex-col justify-end p-3">
          {/* Song title */}
          <div className="text-sm font-medium text-white truncate">
            {/* Song title from store */}
          </div>
          
          {/* Progress bar */}
          <MiniPlayerProgress 
            currentTime={currentTime} 
            duration={duration} 
          />
          
          {/* Controls */}
          <MiniPlayerControls 
            onExpand={expand}
            onClose={close}
          />
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MiniPlayer;
```

#### Features to Include

1. **Minimal UI**
   - Song title and artist (truncated)
   - Small progress bar
   - Play/Pause button
   - "Expand" button to return to full player
   - Close/dismiss button

2. **Optional Enhancements**
   - Mini audio visualizer (waveform)
   - Current lyric line (single line, scrolling)
   - Draggable positioning
   - Resize handle for different sizes

3. **Animations**
   - Slide-in when appearing
   - Slide-out when disappearing
   - Smooth transitions

### Phase 4: App Integration (0.5 day)

```typescript
// App.tsx
import MiniPlayer from '@/components/player/MiniPlayer';

const App: React.FC = () => {
  return (
    <>
      <Toaster />
      <Router>
        <SessionProvider>
          <Routes>
            {/* ... existing routes ... */}
          </Routes>
          
          {/* Mini-player renders outside routes, always available */}
          <MiniPlayer />
        </SessionProvider>
      </Router>
    </>
  );
};
```

### Phase 5: Settings Integration (0.5 day)

Add a toggle in Settings to enable/disable mini-player behavior.

```typescript
// In Settings page
<SettingToggle
  label="Show mini-player when navigating away"
  description="Display a floating player when browsing other pages during playback"
  checked={miniPlayerEnabled}
  onChange={setMiniPlayerEnabled}
/>
```

---

## 🎨 UI/UX Design Considerations

### Visual Design

```
┌──────────────────────────────────────┐
│  ┌──────────────────────────────────┐ │  ← Rounded corners, shadow
│  │     [Visualizer/Album Art]       │ │  ← Background visual
│  │                                   │ │
│  │  ──────────────────────────────  │ │  ← Gradient overlay
│  │  🎵 Song Title - Artist          │ │  ← Truncated text
│  │  ═══════════════○────────────── │ │  ← Mini progress bar
│  │  [◀] [▶/⏸] [▶] [⬚] [✕]        │ │  ← Controls
│  └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### Control Icons
- **Play/Pause**: Standard media controls
- **Expand (⬚)**: Return to full player page
- **Close (✕)**: Dismiss mini-player (stops playback? or just hides?)

### Positioning Options
1. **Fixed corner** (simplest): Bottom-right corner, fixed position
2. **Draggable** (better UX): User can drag to any corner
3. **Snap to corners**: Draggable but snaps to nearest corner when released

### Responsive Behavior
- Desktop: Full mini-player with all features
- Mobile: Possibly a simpler "now playing" bar at bottom

---

## ⚡ Performance Considerations

1. **Lazy Rendering**: Only render mini-player when conditions are met
2. **Memo Components**: Use `React.memo` for subcomponents
3. **Efficient Animations**: Use CSS transforms instead of layout changes
4. **Audio Context**: Already managed by existing store - no duplication
5. **State Subscriptions**: Use Zustand selectors to minimize re-renders

---

## 🔄 Integration with Existing Systems

### WebSocket Sync
The mini-player should participate in the existing WebSocket synchronization:
- When controls are used on mini-player, they broadcast to other devices
- Mini-player receives updates from other devices (e.g., if host pauses from Stage view)

### Session Context
Mini-player should respect the current session context - only show for the active session's playback.

### Performance Controls
If the mini-player includes volume controls, they should sync with the PerformanceControlsPage functionality.

---

## 🎯 Success Criteria

1. **Functional**
   - [ ] Mini-player appears when navigating away from player during playback
   - [ ] Mini-player disappears when returning to player page
   - [ ] Play/pause controls work correctly
   - [ ] Expand button navigates to full player
   - [ ] Progress bar shows current position

2. **User Experience**
   - [ ] Smooth enter/exit animations
   - [ ] Doesn't block important UI elements
   - [ ] Consistent with app's design language
   - [ ] Mobile-friendly (or gracefully hidden on mobile)

3. **Technical**
   - [ ] No memory leaks
   - [ ] Efficient re-renders (verified with React DevTools)
   - [ ] Works with existing WebSocket sync
   - [ ] Respects session boundaries

---

## 📅 Estimated Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Store Enhancement | 0.5 day |
| 2 | Route Detection Hook | 0.5 day |
| 3 | MiniPlayer Component | 2-3 days |
| 4 | App Integration | 0.5 day |
| 5 | Settings Integration | 0.5 day |
| - | Testing & Polish | 1 day |
| **Total** | | **5-6 days** |

---

## 🚀 Future Enhancements

Once the basic mini-player is working, consider these enhancements:

1. **Mini lyrics display**: Show current lyric line in mini-player
2. **Keyboard shortcuts**: Space to play/pause, Esc to expand
3. **Mini queue preview**: Swipe/click to see next song
4. **Picture-in-Picture fallback**: Offer native PiP as option for users who want true always-on-top
5. **Mini-player themes**: Different visual styles (minimal, detailed, visualizer-focused)
6. **Gesture controls**: Swipe to dismiss, double-tap to expand

---

## 📚 References

- [React Portals Documentation](https://react.dev/reference/react-dom/createPortal)
- [YouTube Mini-Player UX Analysis](https://www.youtube.com) - Reference implementation
- [Picture-in-Picture API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Picture-in-Picture_API) - For future native PiP option
- [Document Picture-in-Picture API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Document_Picture-in-Picture_API) - Future consideration when browser support improves
- [Zustand Documentation](https://github.com/pmndrs/zustand) - State management patterns
