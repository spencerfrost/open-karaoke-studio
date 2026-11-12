import {
  attachWordTimestamps,
  parseLrc,
  type WordTimestamp,
} from "@/utils/lrcParser";

import {
  getActiveLineIndex,
  getSweepProgress,
  isWordTimingCrammed,
} from "./activeLineTiming";

describe("getActiveLineIndex", () => {
  it("switches to the next lyric line when aligned words start before the LRC timestamp", () => {
    const lines = attachWordTimestamps(
      parseLrc(
        ["[00:10.000]first line", "[00:12.000]second line starts early"].join(
          "\n",
        ),
      ),
      [
        { word: "first", start: 10.0, end: 10.4, line_index: 0 },
        { word: "line", start: 10.42, end: 10.8, line_index: 0 },
        { word: "second", start: 11.5, end: 11.8, line_index: 1 },
        { word: "line", start: 11.82, end: 12.0, line_index: 1 },
        { word: "starts", start: 12.01, end: 12.28, line_index: 1 },
        { word: "early", start: 12.3, end: 12.65, line_index: 1 },
      ] satisfies WordTimestamp[],
    );

    expect(getActiveLineIndex(lines, 11_700)).toBe(1);
  });

  it("leaves no line active during an instrumental break when aligned words start after the LRC timestamp", () => {
    // The stale LRC tag claims the post-break line starts at 15s, but forced
    // alignment places its first word at 25s — the 13s gap between 12s and 25s
    // is exactly what the backend reports as an instrumental interval. Nothing
    // should be highlighted while that break plays; the progress bar owns it.
    const lines = attachWordTimestamps(
      parseLrc(
        [
          "[00:10.000]Hold On for one more day",
          "[00:15.000]You could sustain (You could sustain)",
        ].join("\n"),
      ),
      [
        { word: "Hold", start: 10.0, end: 10.4, line_index: 0 },
        { word: "On", start: 10.45, end: 10.7, line_index: 0 },
        { word: "for", start: 10.8, end: 11.0, line_index: 0 },
        { word: "one", start: 11.1, end: 11.35, line_index: 0 },
        { word: "more", start: 11.4, end: 11.7, line_index: 0 },
        { word: "day", start: 11.75, end: 12.0, line_index: 0 },
        { word: "You", start: 25.0, end: 25.3, line_index: 1 },
        { word: "could", start: 25.35, end: 25.7, line_index: 1 },
        { word: "sustain", start: 25.75, end: 27.0, line_index: 1 },
      ] satisfies WordTimestamp[],
    );

    expect(getActiveLineIndex(lines, 11_000)).toBe(0);
    expect(getActiveLineIndex(lines, 18_000)).toBe(-1);
    expect(getActiveLineIndex(lines, 25_500)).toBe(1);
  });

  it("keeps a lyric line active through its final aligned word even when a blank line follows", () => {
    const lines = attachWordTimestamps(
      parseLrc(
        [
          "[00:10.000]hold on through the gap",
          "[00:12.000]",
          "[00:15.000]next lyric line",
        ].join("\n"),
      ),
      [
        { word: "hold", start: 10.0, end: 10.3, line_index: 0 },
        { word: "on", start: 10.35, end: 10.52, line_index: 0 },
        { word: "through", start: 10.6, end: 11.0, line_index: 0 },
        { word: "the", start: 11.1, end: 11.24, line_index: 0 },
        { word: "gap", start: 11.3, end: 12.35, line_index: 0 },
        { word: "next", start: 15.0, end: 15.3, line_index: 2 },
        { word: "lyric", start: 15.35, end: 15.7, line_index: 2 },
        { word: "line", start: 15.72, end: 16.0, line_index: 2 },
      ] satisfies WordTimestamp[],
    );

    expect(getActiveLineIndex(lines, 12_200)).toBe(0);
    expect(getActiveLineIndex(lines, 12_500)).toBe(-1);
  });

  it("keeps the final lyric line active through its last aligned word", () => {
    const lines = attachWordTimestamps(
      parseLrc(
        ["[00:10.000]first line", "[00:20.000]final line keeps singing"].join(
          "\n",
        ),
      ),
      [
        { word: "first", start: 10.0, end: 10.3, line_index: 0 },
        { word: "line", start: 10.4, end: 10.8, line_index: 0 },
        { word: "final", start: 20.0, end: 20.4, line_index: 1 },
        { word: "line", start: 20.45, end: 20.7, line_index: 1 },
        { word: "keeps", start: 20.8, end: 21.2, line_index: 1 },
        { word: "singing", start: 21.3, end: 22.9, line_index: 1 },
      ] satisfies WordTimestamp[],
    );

    expect(getActiveLineIndex(lines, 22_000)).toBe(1);
    expect(getActiveLineIndex(lines, 23_100)).toBe(-1);
  });
});

/** Word timings as alignment stored them: [word, start, end, score]. */
function aligned(rows: [string, number, number, number][]): WordTimestamp[] {
  return rows.map(([word, start, end, score]) => ({
    word,
    start,
    end,
    score,
    line_index: 0,
  }));
}

describe("isWordTimingCrammed", () => {
  it("flags a line whose first word holds and whose rest is packed unheard", () => {
    // Blue October "Hate Me": "I" holds 1.2s, nine words follow in ~1s.
    const words = aligned([
      ["I", 24.12, 25.32, 0.6],
      ["was", 25.34, 25.4, 0.05],
      ["just", 25.42, 25.5, 0.04],
      ["calling", 25.52, 25.66, 0.02],
      ["to", 25.68, 25.72, 0.04],
      ["see", 25.74, 25.8, 0.04],
      ["how", 25.82, 25.88, 0.02],
      ["you", 25.91, 25.97, 0.03],
      ["were", 25.99, 26.07, 0.04],
      ["doing", 26.09, 26.19, 0.13],
    ]);

    expect(isWordTimingCrammed(words)).toBe(true);
  });

  it("flags a held word followed by unheard words that are not frame-packed", () => {
    // Kanye West "Stronger": "Work" holds 1.65s, the rest scored ~0.04.
    const words = aligned([
      ["Work", 87.66, 89.31, 0.17],
      ["it", 89.33, 89.37, 0.04],
      ["harder,", 89.39, 89.53, 0.04],
      ["make", 89.56, 89.64, 0.04],
      ["it", 89.66, 89.7, 0.04],
      ["better", 89.72, 89.84, 0.13],
    ]);

    expect(isWordTimingCrammed(words)).toBe(true);
  });

  it("keeps fast singing the aligner heard clearly", () => {
    // Run the Jewels: quick, but well scored.
    const words = aligned([
      ["when", 54.19, 54.31, 0.94],
      ["you", 54.33, 54.43, 0.93],
      ["know", 54.45, 54.63, 0.61],
      ["that", 54.65, 54.75, 0.25],
      ["sometimes", 54.77, 55.13, 0.87],
      ["you", 55.15, 55.25, 0.95],
      ["had", 55.27, 55.42, 0.78],
    ]);

    expect(isWordTimingCrammed(words)).toBe(false);
  });

  it("keeps a held last note", () => {
    const words = aligned([
      ["Just", 225.31, 226.06, 0.84],
      ["what", 226.12, 226.3, 0.94],
      ["you", 226.36, 226.48, 0.96],
      ["mean", 226.64, 229.5, 0.84],
    ]);

    expect(isWordTimingCrammed(words)).toBe(false);
  });

  it("does not judge words that carry no score", () => {
    const words = aligned([
      ["a", 1, 3, 0],
      ["b", 3.02, 3.04, 0],
      ["c", 3.06, 3.08, 0],
    ]).map((word) => ({ ...word, score: undefined }));

    expect(isWordTimingCrammed(words)).toBe(false);
  });
});

describe("getSweepProgress", () => {
  const words = aligned([
    ["Work", 10, 12, 0.17],
    ["it", 12.02, 12.06, 0.04],
    ["harder", 12.08, 14, 0.04],
  ]);

  it("runs from the first word's start to the last word's end", () => {
    expect(getSweepProgress(words, 9)).toBe(0);
    expect(getSweepProgress(words, 12)).toBeCloseTo(0.5);
    expect(getSweepProgress(words, 15)).toBe(1);
  });
});
