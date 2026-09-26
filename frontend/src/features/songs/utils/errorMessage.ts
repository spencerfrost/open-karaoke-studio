export const SONG_ERROR_FALLBACK =
  "This song couldn't be processed. The original download or audio separation failed.";

const AGE_RESTRICTED_PATTERN = /confirm your age|age-restricted/i;

/**
 * Prefix a raw failure reason with a plain-language hint when the pattern is
 * recognized, while keeping the original text visible below it — the raw
 * text is what makes the failure debuggable.
 */
export const humanizeSongError = (
  errorMessage: string | null | undefined,
): { hint?: string; detail: string } => {
  const detail = errorMessage?.trim() || SONG_ERROR_FALLBACK;
  if (errorMessage && AGE_RESTRICTED_PATTERN.test(errorMessage)) {
    return { hint: "This video is age-restricted on YouTube.", detail };
  }
  return { detail };
};
