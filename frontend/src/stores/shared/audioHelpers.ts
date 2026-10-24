/**
 * Web Audio API helper functions
 */

/**
 * Normalize a value between 0 and 1
 */
export function normalizeVolume(volume: number): number {
  return Math.max(0, Math.min(1, volume));
}
