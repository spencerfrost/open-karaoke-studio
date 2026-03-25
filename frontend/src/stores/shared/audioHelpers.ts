/**
 * Web Audio API helper functions
 */

import { GrainParams } from "./types";

// Tone.js GrainPlayer configuration for pitch-preserving speed control
// Dynamic grain sizing reduces transient artifacts (doubling/slap delay) at slower speeds
export const BASE_GRAIN_SIZE = 0.07; // 70ms base grain size
export const GRAIN_OVERLAP_RATIO = 0.5; // 50% overlap for smooth crossfade

/**
 * Calculate grain size and overlap based on playback speed
 * Smaller grains at slower speeds reduce transient smearing (snare doubling, etc.)
 * Formula: grainSize = baseSize * speed
 */
export function getGrainParams(speed: number): GrainParams {
  const grainSize = BASE_GRAIN_SIZE * speed;
  const overlap = grainSize * GRAIN_OVERLAP_RATIO;
  return { grainSize, overlap };
}

/**
 * Normalize a value between 0 and 1
 */
export function normalizeVolume(volume: number): number {
  return Math.max(0, Math.min(1, volume));
}

/**
 * Clamp playback speed to valid range (0.5x to 2.0x)
 */
export function clampSpeed(speed: number): number {
  return Math.max(0.5, Math.min(2.0, speed));
}
