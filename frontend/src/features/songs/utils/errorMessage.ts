export const SONG_ERROR_FALLBACK =
  "This song couldn't be processed. The original download or audio separation failed.";

// Each pattern maps a raw failure reason to a plain-language hint. The
// server-busy and network ones only stick after the automatic retries ran out.
const ERROR_HINTS: { pattern: RegExp; hint: string }[] = [
  {
    pattern: /confirm your age|age-restricted/i,
    hint: "This video is age-restricted on YouTube.",
  },
  {
    pattern: /out of memory/i,
    hint: "The server was too busy to process it, even after a few tries.",
  },
  {
    pattern:
      /name resolution|timed out|connection (reset|refused|aborted)|temporary failure|network is unreachable|HTTP Error 5\d\d/i,
    hint: "Couldn't reach YouTube to download it, even after a few tries.",
  },
];

/**
 * Prefix a raw failure reason with a plain-language hint when the pattern is
 * recognized, while keeping the original text visible below it — the raw
 * text is what makes the failure debuggable.
 */
export const humanizeSongError = (
  errorMessage: string | null | undefined,
): { hint?: string; detail: string } => {
  const detail = errorMessage?.trim() || SONG_ERROR_FALLBACK;
  const match = errorMessage
    ? ERROR_HINTS.find(({ pattern }) => pattern.test(errorMessage))
    : undefined;
  return match ? { hint: match.hint, detail } : { detail };
};
