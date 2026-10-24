import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

/**
 * The song position in seconds, rounded down to `stepSeconds`.
 *
 * The store updates the position every animation frame. A component that
 * subscribes to it directly re-renders 60 times a second, which the TV can't
 * afford. Rounding inside the selector means the component only re-renders
 * when the rounded value changes, so pick the coarsest step that still looks
 * smooth for what it draws.
 */
export function useSongPosition(stepSeconds: number): number {
  return useKaraokePlayerStore(
    (s) => Math.floor(s.currentTime / stepSeconds) * stepSeconds,
  );
}
