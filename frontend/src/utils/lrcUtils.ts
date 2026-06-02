/**
 * LRC (Lyric) file utilities for parsing and modifying synced lyrics
 */

/**
 * Apply a timing offset to all timestamps in LRC content
 *
 * The offset semantics match runtime behavior where:
 * - Positive offset = lyrics appear earlier (we pretend playback is further along)
 * - Negative offset = lyrics appear later (we pretend playback is behind)
 *
 * To permanently bake this in, we SUBTRACT the offset from timestamps:
 * - Positive offset -> subtract from timestamps -> lyrics trigger earlier
 * - Negative offset -> add to timestamps -> lyrics trigger later
 *
 * @param lrcContent - Original LRC string
 * @param offsetMs - Offset in milliseconds (positive = lyrics earlier, negative = lyrics later)
 * @returns Modified LRC string with adjusted timestamps
 */
export function applyOffsetToLrc(lrcContent: string, offsetMs: number): string {
  if (offsetMs === 0) return lrcContent;

  // LRC timestamp format: [mm:ss.xx] or [mm:ss.xxx]
  // Regex to match timestamps
  const timestampRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/g;

  return lrcContent.replace(timestampRegex, (_match, minutes, seconds, ms) => {
    // Parse current timestamp to milliseconds
    // Handle both 2-digit (centiseconds) and 3-digit (milliseconds) precision
    const msValue =
      ms.length === 2
        ? parseInt(ms) * 10 // Convert centiseconds to milliseconds
        : parseInt(ms);

    const currentMs =
      parseInt(minutes) * 60000 + parseInt(seconds) * 1000 + msValue;

    // Subtract offset to match runtime behavior (ensure non-negative)
    const newMs = Math.max(0, currentMs - offsetMs);

    // Convert back to LRC format
    const newMinutes = Math.floor(newMs / 60000);
    const newSeconds = Math.floor((newMs % 60000) / 1000);
    const newMillis = newMs % 1000;

    // Return formatted timestamp (match original precision)
    const msPrecision = ms.length;
    const msString =
      msPrecision === 2
        ? String(Math.floor(newMillis / 10)).padStart(2, "0")
        : String(newMillis).padStart(3, "0");

    return `[${String(newMinutes).padStart(2, "0")}:${String(newSeconds).padStart(2, "0")}.${msString}]`;
  });
}

/**
 * Check if a string contains valid LRC timestamps
 * @param content - String to check
 * @returns true if the content contains valid LRC timestamps
 */
export function hasLrcTimestamps(content: string): boolean {
  const timestampRegex = /\[\d{2}:\d{2}\.\d{2,3}\]/;
  return timestampRegex.test(content);
}

// Export LRC parser for count-in system
export {
  parseLrcWithCountIn,
  attachWordTimestamps,
  type ParsedLrcData,
  type CountInTrigger,
  type LrcLine,
  type InstrumentalGap,
  type InstrumentalInterval,
  type WordTimestamp,
} from "./lrcParser";
