import { Song } from "@/types/Song";

/**
 * Get song duration in seconds
 */
export const getSongDuration = (song: Song): number => {
  return song.duration ?? 0;
};

/**
 * Where a hover preview should start, in seconds.
 *
 * Aims ~30% into the track so the preview lands past the intro (usually near a
 * chorus) rather than on silence. Backs off far enough from the end that a full
 * preview window still fits. Falls back to the start of the track when the
 * duration is unknown.
 */
export const getPreviewStartSeconds = (
  durationSeconds: number | undefined,
  previewWindowSeconds: number,
): number => {
  if (
    durationSeconds === undefined ||
    !Number.isFinite(durationSeconds) ||
    durationSeconds <= 0
  ) {
    return 0;
  }

  const target = durationSeconds * 0.3;
  const latest = durationSeconds - previewWindowSeconds - 2;
  return Math.max(0, Math.min(target, latest));
};
