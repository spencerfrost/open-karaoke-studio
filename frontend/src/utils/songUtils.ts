import { Song } from "@/types/Song";

/**
 * Get song duration in seconds
 */
export const getSongDuration = (song: Song): number => {
  return song.duration ?? 0;
};
