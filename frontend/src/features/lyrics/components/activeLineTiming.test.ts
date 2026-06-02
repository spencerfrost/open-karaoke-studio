import { attachWordTimestamps, parseLrc, type WordTimestamp } from "@/utils/lrcParser";

import { getActiveLineIndex } from "./activeLineTiming";

describe("getActiveLineIndex", () => {
  it("switches to the next lyric line when aligned words start before the LRC timestamp", () => {
    const lines = attachWordTimestamps(
      parseLrc(
        [
          "[00:10.000]first line",
          "[00:12.000]second line starts early",
        ].join("\n"),
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
        [
          "[00:10.000]first line",
          "[00:20.000]final line keeps singing",
        ].join("\n"),
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