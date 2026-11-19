/**
 * Shared types for karaoke player stores
 */

// Control value type for WebSocket communication
export type ControlValue = number | string | boolean | null;

// Performance state from backend (snake_case from WebSocket)
export interface PerformanceState {
  vocal_volume: number;
  backing_vocal_volume: number;
  instrumental_volume: number;
  /**
   * The lead vocal in the singer's headphones, 0-1. Null or missing when the
   * stage has no headphones output, so phones hide its fader.
   */
  headphones_volume?: number | null;
  lyrics_size: "small" | "medium" | "large";
  lyrics_offset: number;
  current_time: number;
  duration: number;
  is_playing: boolean;
  current_song_id?: string | null;
  is_ready?: boolean;
}

// Mini-player position interface
export interface MiniPlayerPosition {
  x: number;
  y: number;
}

// Local update tracking for debouncing WebSocket echoes
export interface LocalUpdateTracker {
  [key: string]: { value: unknown; timestamp: number };
}
