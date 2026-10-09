import { describe, expect, it } from "vitest";
import { humanizeSongError, SONG_ERROR_FALLBACK } from "./errorMessage";

describe("humanizeSongError", () => {
  it("falls back when there's no reason", () => {
    expect(humanizeSongError(null)).toEqual({ detail: SONG_ERROR_FALLBACK });
  });

  it("keeps an unrecognized reason as-is", () => {
    expect(humanizeSongError("Video unavailable")).toEqual({
      detail: "Video unavailable",
    });
  });

  it.each([
    ["Sign in to confirm your age", "age-restricted"],
    ["CUDA out of memory. Tried to allocate 2.00 MiB.", "too busy"],
    [
      "Failed to download YouTube video: [Errno -3] Temporary failure in name resolution",
      "Couldn't reach YouTube",
    ],
  ])("adds a hint for %s", (reason, hint) => {
    const result = humanizeSongError(reason);
    expect(result.hint).toContain(hint);
    expect(result.detail).toBe(reason);
  });
});
