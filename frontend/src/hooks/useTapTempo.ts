import { useState, useCallback, useRef } from "react";

interface UseTapTempoOptions {
  minTaps?: number; // Minimum taps before calculating BPM (default: 3)
  maxTaps?: number; // Maximum taps to keep in history (default: 8)
  onBpmChange?: (bpm: number) => void; // Callback when BPM changes
}

interface UseTapTempoReturn {
  bpm: number | null;
  tapCount: number;
  handleTap: () => void;
  reset: () => void;
  isActive: boolean; // Whether user is actively tapping
  hasUnsavedChanges: boolean; // Whether BPM has changed but not saved
}

/**
 * Hook for implementing tap tempo functionality.
 *
 * Uses linear regression over raw tap timestamps (rather than averaging
 * consecutive intervals) for a more stable BPM estimate — a single mistimed
 * tap skews only one point in the regression instead of two adjacent intervals.
 *
 * Automatically resets the tap history when a gap between taps exceeds
 * max(2000ms, 2 × current beat period), so stale taps from a previous attempt
 * never contaminate a new tapping session.
 */
export const useTapTempo = (
  options: UseTapTempoOptions = {},
): UseTapTempoReturn => {
  const { minTaps = 3, maxTaps = 8, onBpmChange } = options;

  const [tapTimes, setTapTimes] = useState<number[]>([]);
  const [bpm, setBpm] = useState<number | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Ref so the setTapTimes updater can read the latest BPM without a stale closure
  const bpmRef = useRef<number | null>(null);

  const handleTap = useCallback(() => {
    const now = Date.now();

    setTapTimes((prev) => {
      // Timeout reset: if the gap since the last tap is too long, start fresh.
      // Threshold = max(2000ms, 2 × current beat period) so slow songs don't
      // reset prematurely while fast songs clear stale data quickly.
      if (prev.length > 0) {
        const gap = now - prev[prev.length - 1];
        const currentPeriodMs = bpmRef.current ? 60000 / bpmRef.current : 0;
        const resetThreshold = Math.max(2000, 2 * currentPeriodMs);
        if (gap > resetThreshold) {
          return [now];
        }
      }

      const newTaps = [...prev, now].slice(-maxTaps);

      if (newTaps.length >= minTaps) {
        const n = newTaps.length;

        // Linear regression: fit t_i = t_0 + i * slope, solve for slope (ms/beat).
        // x = beat index [0..n-1], y = raw timestamp
        let sumX = 0,
          sumY = 0,
          sumXY = 0,
          sumX2 = 0;
        for (let i = 0; i < n; i++) {
          sumX += i;
          sumY += newTaps[i];
          sumXY += i * newTaps[i];
          sumX2 += i * i;
        }
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const roundedBpm = Math.round((60000 / slope) * 10) / 10;

        bpmRef.current = roundedBpm;
        setBpm(roundedBpm);
        setHasUnsavedChanges(true);
        onBpmChange?.(roundedBpm);
      }

      return newTaps;
    });
  }, [minTaps, maxTaps, onBpmChange]);

  const reset = useCallback(() => {
    setTapTimes([]);
    setBpm(null);
    bpmRef.current = null;
    setHasUnsavedChanges(false);
  }, []);

  const isActive = tapTimes.length > 0;

  return {
    bpm,
    tapCount: tapTimes.length,
    handleTap,
    reset,
    isActive,
    hasUnsavedChanges,
  };
};
