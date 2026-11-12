/**
 * WebSocket synchronization utilities
 * Handles debouncing and preventing echo updates
 */

import { LocalUpdateTracker } from "./types";

// Ignore WebSocket updates for 1 second after local change
export const LOCAL_UPDATE_DEBOUNCE_MS = 1000;

/**
 * Check if a WebSocket update should be ignored based on recent local updates
 * This prevents echoes and stale broadcasts from undoing a local change
 */
export function shouldIgnoreWebSocketUpdate(
  lastLocalUpdate: LocalUpdateTracker,
  control: string,
  value: unknown,
): boolean {
  const localUpdate = lastLocalUpdate[control];
  if (!localUpdate) return false;

  const timeSinceLocalUpdate = Date.now() - localUpdate.timestamp;
  const isWithinDebounceWindow =
    timeSinceLocalUpdate < LOCAL_UPDATE_DEBOUNCE_MS;

  // For currentTime, allow small differences due to precision/timing
  if (
    control === "current_time" &&
    typeof value === "number" &&
    typeof localUpdate.value === "number"
  ) {
    const timeDifference = Math.abs(value - localUpdate.value);
    const isSimilarTime = timeDifference < 0.5; // Within 0.5 seconds
    return isSimilarTime && isWithinDebounceWindow;
  }

  // For other controls the local change wins outright for the window, not
  // only against its own echo: the stage re-broadcasts the full state every
  // few hundred ms, so a broadcast sent just before the server saw this change
  // still carries the old value and would snap the control back.
  return isWithinDebounceWindow;
}

/**
 * Track a local update to prevent WebSocket echoes
 */
export function trackLocalUpdate(
  lastLocalUpdate: LocalUpdateTracker,
  control: string,
  value: unknown,
): void {
  lastLocalUpdate[control] = {
    value,
    timestamp: Date.now(),
  };
}

/**
 * Clear all tracked updates (e.g., when loading a new song)
 */
export function clearLocalUpdates(lastLocalUpdate: LocalUpdateTracker): void {
  Object.keys(lastLocalUpdate).forEach((key) => delete lastLocalUpdate[key]);
}

/**
 * Convert camelCase to snake_case for backend communication
 */
export function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => "_" + letter.toLowerCase());
}
