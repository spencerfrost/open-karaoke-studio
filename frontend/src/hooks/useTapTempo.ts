import { useState, useCallback } from "react";

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
 * Hook for implementing tap tempo functionality
 * Calculates BPM based on user taps with configurable minimum taps required
 * BPM persists until explicitly reset - no auto-timeout
 */
export const useTapTempo = (
  options: UseTapTempoOptions = {}
): UseTapTempoReturn => {
  const {
    minTaps = 3,
    maxTaps = 8,
    onBpmChange,
  } = options;

  const [tapTimes, setTapTimes] = useState<number[]>([]);
  const [bpm, setBpm] = useState<number | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const handleTap = useCallback(() => {
    const now = Date.now();

    setTapTimes((prev) => {
      const newTaps = [...prev, now].slice(-maxTaps);

      // Calculate BPM only if we have enough taps
      if (newTaps.length >= minTaps) {
        // Calculate intervals between consecutive taps
        const intervals: number[] = [];
        for (let i = 1; i < newTaps.length; i++) {
          intervals.push(newTaps[i] - newTaps[i - 1]);
        }

        // Average interval in milliseconds
        const avgInterval = intervals.reduce((a, b) => a + b) / intervals.length;

        // Convert to BPM (60000 ms per minute / interval in ms)
        const calculatedBpm = 60000 / avgInterval;

        // Round to 1 decimal place
        const roundedBpm = Math.round(calculatedBpm * 10) / 10;

        setBpm(roundedBpm);
        setHasUnsavedChanges(true);

        // Notify callback if provided
        if (onBpmChange) {
          onBpmChange(roundedBpm);
        }
      }

      return newTaps;
    });
  }, [minTaps, maxTaps, onBpmChange]);

  const reset = useCallback(() => {
    setTapTimes([]);
    setBpm(null);
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
