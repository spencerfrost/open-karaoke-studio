import { Song } from '@/types/Song';

/**
 * Get song duration in seconds, preferring the new duration field over durationMs
 */
export const getSongDuration = (song: Song): number => {
  // Prefer new duration field (seconds)
  if (song.duration !== undefined) {
    return song.duration;
  }
  
  // Fallback to old durationMs field (milliseconds) during migration
  if (song.durationMs !== undefined) {
    return song.durationMs / 1000;
  }
  
  // Default fallback
  return 0;
};

/**
 * Get song duration in milliseconds for backwards compatibility
 */
export const getSongDurationMs = (song: Song): number => {
  return Math.round(getSongDuration(song) * 1000);
};