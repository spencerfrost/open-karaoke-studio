# Instrumental Intervals Frontend Integration Guide

## Overview

**Instrumental intervals** are song sections where there are no lyrics—intros, breaks, bridges, etc. The backend now detects these automatically using WhisperX word-timing gaps and exposes them via the alignment API.

On the frontend, you consume these intervals and render a **duration-based progress bar** during instrumental windows, giving singers a visual countdown to re-entry without requiring BPM calculation.

---

## Data Flow

```
Backend alignment job (WhisperX)
    ↓
Derives gaps between words → Builds instrumental_intervals[]
    ↓
Persists to DB in word_synced_lyrics JSON
    ↓
GET /api/lyrics/songs/{songId}/alignment
    ↓
useLyricsAlignment() hook (frontend)
    ↓
Merges into ParsedLrcData.instrumentalIntervals
    ↓
KaraokeLyricsRenderer renders progress bar
```

---

## Data Structure

### InstrumentalInterval Type

```typescript
interface InstrumentalInterval {
  start: number;              // seconds (e.g., 44.381)
  end: number;                // seconds (e.g., 51.91)
  duration: number;           // seconds (e.g., 7.529)
  lead_in_start: number;      // seconds (e.g., 50.41) — when UI should start showing timer
  next_line_index: number;    // line index where lyric re-entry occurs
  confidence: number;         // 0.0–1.0, higher = more confident this is instrumental
  source: string;             // "whisperx_gap" (reserved for future ML/audio-based detection)
}
```

### Example Payload

```json
{
  "instrumental_intervals": [
    {
      "start": 0.0,
      "end": 11.881,
      "duration": 11.881,
      "lead_in_start": 10.381,
      "next_line_index": 0,
      "confidence": 1.0,
      "source": "whisperx_gap"
    },
    {
      "start": 44.381,
      "end": 51.91,
      "duration": 7.529,
      "lead_in_start": 50.41,
      "next_line_index": 10,
      "confidence": 0.941,
      "source": "whisperx_gap"
    }
  ]
}
```

---

## Frontend Integration Points

### 1. Fetching from the Hook

```typescript
// frontend/src/hooks/api/useLyricsAlignment.ts
// Already exports instrumental intervals

const { 
  words: alignmentWords,
  instrumentalIntervals,  // ← NEW
  meanScore,
  isLoading,
  error
} = useLyricsAlignment(songId);
```

Returns `null` if no alignment exists yet, or an `InstrumentalInterval[]` if alignment is complete.

### 2. Parsing into ParsedLrcData

```typescript
// frontend/src/features/lyrics/components/LyricsDisplay.tsx
// Already merges intervals into parsed data

const parsedLrcDataWithWords = useMemo(() => {
  if (!parsedLrcData) return null;
  return {
    ...parsedLrcData,
    lines: attachWordTimestamps(parsedLrcData.lines, alignmentWords),
    ...(instrumentalIntervals ? { instrumentalIntervals } : {}),
  };
}, [parsedLrcData, alignmentWords, instrumentalIntervals]);
```

The renderer receives `ParsedLrcData` with optional `instrumentalIntervals` field.

### 3. Consuming in the Renderer

```typescript
// frontend/src/features/lyrics/components/KaraokeLyricsRenderer.tsx
// Already detects active instrumental interval and renders progress bar

const activeInstrumentalInterval = useMemo(() => {
  return parsedData.instrumentalIntervals?.find(
    (interval) =>
      currentTimeSec >= interval.start && currentTimeSec < interval.end,
  );
}, [parsedData.instrumentalIntervals, currentTimeSec]);

// Render progress bar during instrumental window
if (activeInstrumentalInterval) {
  const elapsed = currentTimeSec - activeInstrumentalInterval.start;
  const duration = activeInstrumentalInterval.end - activeInstrumentalInterval.start;
  const progress = Math.max(0, Math.min(1, elapsed / duration));

  return {
    progress,      // 0.0 → 1.0 as we move through the instrumental
    currentBeatIndex: -1,
  };
}
```

---

## Current Implementation Status

✅ **Already implemented:**
- Alignment hook exposes `instrumentalIntervals`
- LyricsDisplay merges intervals into `ParsedLrcData`
- KaraokeLyricsRenderer detects active interval and calculates progress
- Progress bar renders during instrumental windows (when `showProgressBar=true` on count-in style config)
- BPM countdown numbers/icons are suppressed during instrumental mode (no beat counting needed)
- **Extra line break rendering**: active instrumental window's next lyric line gets marked as "hasCountIn" to add visual spacing

**What still needs work:**
- Styling/animations for the progress bar during instrumental mode
- Optional: Confidence-based filtering (hide progress bars for low-confidence intervals)
- Optional: UI affordance for "lead-in" phase (1.5s pre-roll visibility)
- Optional: Accessibility labels for instrumental sections

---

## Using Instrumental Intervals in New Code

### Basic Pattern

```typescript
import { useLyricsAlignment } from "@/hooks/api/useLyricsAlignment";
import { parseLrcWithCountIn } from "@/utils/lrcParser";
import type { InstrumentalInterval } from "@/utils/lrcParser";

function MyLyricsComponent() {
  const { instrumentalIntervals } = useLyricsAlignment(songId);
  const [currentTime, setCurrentTime] = useState(0);

  // Find if we're currently in an instrumental window
  const activeInterval = instrumentalIntervals?.find(
    (i) => currentTime >= i.start && currentTime < i.end
  );

  if (activeInterval) {
    const progress = (currentTime - activeInterval.start) / activeInterval.duration;
    return (
      <div className="progress-bar">
        <div style={{ width: `${progress * 100}%` }} />
        <span>Come in at {activeInterval.end.toFixed(1)}s</span>
      </div>
    );
  }

  return null;
}
```

### Filtering by Confidence

If you want to only show high-confidence intervals:

```typescript
const highConfidenceIntervals = instrumentalIntervals?.filter((i) => i.confidence > 0.8) ?? [];
```

### Getting Next Lyric Line Info

```typescript
const activeInterval = instrumentalIntervals?.find(...);
if (activeInterval) {
  const nextLineIndex = activeInterval.next_line_index;
  const nextLine = parsedData.lines[nextLineIndex];
  console.log(`Lyric re-entry: "${nextLine.content}"`);
}
```

---

## Testing

### Unit Test Pattern

```typescript
import { render } from "@testing-library/react";
import InstrumentalProgressBar from "./InstrumentalProgressBar";
import type { InstrumentalInterval } from "@/utils/lrcParser";

it("should show progress during instrumental interval", () => {
  const intervals: InstrumentalInterval[] = [
    {
      start: 10,
      end: 20,
      duration: 10,
      lead_in_start: 8.5,
      next_line_index: 5,
      confidence: 0.95,
      source: "whisperx_gap",
    },
  ];

  const { getByText } = render(
    <InstrumentalProgressBar
      instrumentalIntervals={intervals}
      currentTime={15} // Midway through instrumental
    />
  );

  expect(getByText(/50/)).toBeInTheDocument(); // 50% progress
});

it("should hide progress bar when not in instrumental", () => {
  const intervals: InstrumentalInterval[] = [{ /* ... */ }];
  const { queryByText } = render(
    <InstrumentalProgressBar
      instrumentalIntervals={intervals}
      currentTime={25} // Past the instrumental
    />
  );

  expect(queryByText(/progress/i)).not.toBeInTheDocument();
});
```

### Integration Test Pattern

```typescript
import { rest } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  rest.get("/api/lyrics/songs/:songId/alignment", (req, res, ctx) => {
    return res(
      ctx.json({
        alignment: {
          words: [...],
          instrumental_intervals: [
            {
              start: 0,
              end: 12,
              duration: 12,
              lead_in_start: 10.5,
              next_line_index: 0,
              confidence: 1.0,
              source: "whisperx_gap",
            },
          ],
        },
      })
    );
  })
);

it("should fetch and display instrumental intervals", async () => {
  const { getByText } = render(<LyricsDisplay songId="test-123" />);
  
  await waitFor(() => {
    expect(getByText(/instrumental/i)).toBeInTheDocument();
  });
});
```

---

## Examples in Codebase

- **Data consumption**: [useLyricsAlignment.ts](../frontend/src/hooks/api/useLyricsAlignment.ts)
- **Type definitions**: [lrcParser.ts](../frontend/src/utils/lrcParser.ts) — `InstrumentalInterval` interface
- **Renderer integration**: [KaraokeLyricsRenderer.tsx](../frontend/src/features/lyrics/components/KaraokeLyricsRenderer.tsx) — `activeInstrumentalInterval` logic

---

## Fallback Behavior

If `instrumentalIntervals` is `null` or `undefined`:
- Frontend falls back to heuristic gap detection (`findInstrumentalGaps()` from LRC blank lines)
- Progress bar styling still works but is driven by `countInTriggers` (BPM-based) instead
- No breaking changes to existing lyrics display

---

## Performance Notes

- **Memoization**: `activeInstrumentalInterval` is memoized in the renderer to avoid recalculation on every playback tick
- **Filtering**: If you filter by confidence, do it in a `useMemo` to avoid re-computing on every render
- **No polling**: Intervals are fetched once when song loads, not polled during playback

---

## Future Enhancements

1. **Audio energy refinement**: Add optional low-vocal-energy verification to reduce false positives
2. **ML confidence scoring**: Replace simple gap-duration heuristic with trained classifier
3. **Backup vocals handling**: If three-track separation is used, skip intervals where backing vocals exist but main vocal is silent
4. **User corrections**: UI for singers to mark instrumental windows as incorrect and provide feedback
5. **Outro handling**: Currently includes intro gaps; pode extend to trailing post-lyric silence if desired

---

## Debugging

### Check alignment was computed
```bash
curl http://localhost:5123/api/lyrics/songs/{songId}/alignment | jq '.alignment | {word_count, interval_count: (.instrumental_intervals | length)}'
```

### View all intervals
```bash
curl http://localhost:5123/api/lyrics/songs/{songId}/alignment | jq '.alignment.instrumental_intervals'
```

### Check renderer receives them
```typescript
// In browser console, add to KaraokeLyricsRenderer:
console.log("Active interval:", activeInstrumentalInterval);
console.log("All intervals:", parsedData.instrumentalIntervals);
```

### Low-confidence intervals
```bash
curl http://localhost:5123/api/lyrics/songs/{songId}/alignment | jq '.alignment.instrumental_intervals | map(select(.confidence < 0.7))'
```
