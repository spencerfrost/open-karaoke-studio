import { parseLrc } from "@/utils/lrcParser";

/** How long the prompt stays up in a song without timed lyrics, in seconds. */
export const UNTIMED_PROMPT_SECONDS = 15;

/**
 * When, in song seconds, the "open your phone" prompt gives way to the song.
 *
 * The intro is the one stretch where a singer's hands and eyes are free, so the
 * prompt lasts until the first sung line comes up, and never sits over the
 * words. `lyricsOffsetMs` moves the lyrics the way the renderer does: a line
 * at `t` ms shows once `songTime * 1000 + offset >= t`. A song without timed
 * lyrics gets a fixed stretch instead.
 */
export function phonePromptEnd(
  syncedLyrics: string | null | undefined,
  lyricsOffsetMs: number,
): number {
  const firstSung = parseLrc(syncedLyrics ?? "").find((line) => !line.isBlank);
  if (!firstSung) return UNTIMED_PROMPT_SECONDS;
  return Math.max(0, (firstSung.timestamp - lyricsOffsetMs) / 1000);
}
