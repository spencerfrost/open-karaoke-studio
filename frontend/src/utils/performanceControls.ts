/**
 * Utility functions for performance controls
 */

export type LyricsSize = "small" | "medium" | "large";

/**
 * Convert lyrics size string to numeric value for controls
 */
export function getLyricsSizeValue(lyricsSize: LyricsSize): number {
  switch (lyricsSize) {
    case "small":
      return 1;
    case "medium":
      return 2;
    case "large":
      return 3;
    default:
      return 2;
  }
}

/**
 * Convert numeric value back to lyrics size string
 */
export function parseLyricsSize(value: number): LyricsSize {
  switch (value) {
    case 1:
      return "small";
    case 2:
      return "medium";
    case 3:
      return "large";
    default:
      return "medium";
  }
}

/**
 * Get display label for lyrics size
 */
export function getLyricsSizeLabel(lyricsSize: LyricsSize): string {
  switch (lyricsSize) {
    case "small":
      return "Small";
    case "medium":
      return "Medium";
    case "large":
      return "Large";
    default:
      return "Medium";
  }
}

/**
 * Toggle volume between 0 and 1 (or custom max value)
 */
export function toggleVolume(
  currentVolume: number,
  maxVolume: number = 1,
): number {
  return currentVolume > 0 ? 0 : maxVolume;
}

/**
 * Get timing offset description
 */
export function getTimingOffsetDescription(offset: number): string {
  if (offset === 0) return "Lyrics are synced";
  if (offset > 0) return "Lyrics appear earlier";
  return "Lyrics appear later";
}
