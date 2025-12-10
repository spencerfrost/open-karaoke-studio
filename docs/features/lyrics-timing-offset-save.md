# Lyrics Timing Offset Save Feature

## Overview

When a user adjusts the lyrics timing offset, provide a "Save" button that permanently applies the offset to the synced lyrics by recalculating all timestamp values.

## Current Behavior

- User adjusts `lyricsOffset` in the PlayerSidebar (stored in Zustand store)
- Offset is applied at render time: `currentMillisecond={(currentTime * 1000) + lyricsOffset}`
- Offset is lost when user navigates away or reloads

## Proposed Behavior

1. When `lyricsOffset !== 0`, show a "Save" button next to the reset button
2. Clicking "Save" applies the offset to all timestamps in the LRC content
3. Updated lyrics are sent to the backend via `PUT /api/songs/{id}`
4. Offset resets to 0 after successful save

## Implementation Steps

### 1. LRC Timestamp Parser/Modifier

Create a utility function in `frontend/src/utils/lrcUtils.ts`:

```typescript
/**
 * Apply a timing offset to all timestamps in LRC content
 * @param lrcContent - Original LRC string
 * @param offsetMs - Offset in milliseconds (positive = later, negative = earlier)
 * @returns Modified LRC string with adjusted timestamps
 */
export function applyOffsetToLrc(lrcContent: string, offsetMs: number): string {
  // LRC timestamp format: [mm:ss.xx] or [mm:ss.xxx]
  // Regex to match timestamps
  const timestampRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/g;
  
  return lrcContent.replace(timestampRegex, (match, minutes, seconds, ms) => {
    // Parse current timestamp to milliseconds
    const currentMs = 
      parseInt(minutes) * 60000 + 
      parseInt(seconds) * 1000 + 
      parseInt(ms.padEnd(3, '0'));
    
    // Apply offset (ensure non-negative)
    const newMs = Math.max(0, currentMs + offsetMs);
    
    // Convert back to LRC format
    const newMinutes = Math.floor(newMs / 60000);
    const newSeconds = Math.floor((newMs % 60000) / 1000);
    const newMillis = newMs % 1000;
    
    // Return formatted timestamp (match original precision)
    const msPrecision = ms.length;
    const msString = msPrecision === 2 
      ? String(Math.floor(newMillis / 10)).padStart(2, '0')
      : String(newMillis).padStart(3, '0');
    
    return `[${String(newMinutes).padStart(2, '0')}:${String(newSeconds).padStart(2, '0')}.${msString}]`;
  });
}
```

### 2. Update PlayerSidebar Component

In `PlayerSidebar.tsx`, add save functionality:

```typescript
// Add to imports
import { useSongs } from '@/hooks/api/useSongs';
import { applyOffsetToLrc } from '@/utils/lrcUtils';

// Inside SidebarContent component
const { useUpdateSong } = useSongs();
const updateSongMutation = useUpdateSong();

// Get current song's synced lyrics from player hook or store
const { lyrics, songId } = useKaraokePlayerStore();

const handleSaveOffset = () => {
  if (!songId || !lyrics || lyricsOffset === 0) return;
  
  const updatedLyrics = applyOffsetToLrc(lyrics, lyricsOffset);
  
  updateSongMutation.mutate({
    id: songId,
    syncedLyrics: updatedLyrics,
  }, {
    onSuccess: () => {
      setLyricsOffset(0); // Reset offset after save
      toast.success('Lyrics timing saved!');
    },
    onError: (error) => {
      toast.error(`Failed to save: ${error.message}`);
    }
  });
};
```

### 3. UI Changes

Add save button in the timing offset section (after reset button):

```tsx
{/* Save button - only show when offset is non-zero */}
{lyricsOffset !== 0 && (
  <Button
    variant="ghost"
    size="sm"
    onClick={handleSaveOffset}
    disabled={updateSongMutation.isPending}
    className="text-xs text-orange-peel hover:text-orange-peel/80"
  >
    {updateSongMutation.isPending ? 'Saving...' : 'Save'}
  </Button>
)}
```

### 4. Backend

No backend changes needed - the existing `PUT /api/songs/{id}` endpoint already accepts `syncedLyrics` updates.

## Edge Cases to Handle

- **No synced lyrics**: Hide save button if song only has plain lyrics
- **Negative timestamps**: Clamp to 0 (can't have negative time)
- **Mutation in progress**: Disable button and show loading state
- **Player needs to refetch lyrics**: After save, the player should reload lyrics from the server (invalidate TanStack Query cache)

## Testing

1. Load a song with synced lyrics
2. Adjust timing offset (e.g., +500ms)
3. Click Save
4. Verify offset resets to 0
5. Reload page - lyrics should still be correctly timed
