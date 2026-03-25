/**
 * Shared types for karaoke player stores
 */

// Control value type for WebSocket communication
export type ControlValue = number | string | boolean;

// Performance state from backend (snake_case from WebSocket)
export interface PerformanceState {
  vocal_volume: number;
  backing_vocal_volume: number;
  instrumental_volume: number;
  lyrics_size: "small" | "medium" | "large";
  lyrics_offset: number;
  current_time: number;
  duration: number;
  is_playing: boolean;
  current_song_id?: string | null;
  is_ready?: boolean;
  playback_speed: number;
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

// Grain parameters for Tone.js GrainPlayer
export interface GrainParams {
  grainSize: number;
  overlap: number;
}
