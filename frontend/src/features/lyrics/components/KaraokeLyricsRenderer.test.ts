import { parseLrc } from "@/utils/lrcParser";

import {
  getInstrumentalSeparatorLineIndex,
  getInstrumentalTargetLineIndex,
} from "./KaraokeLyricsRenderer";
import type { ParsedLrcData } from "@/utils/lrcUtils";

describe("getInstrumentalSeparatorLineIndex", () => {
  it("anchors the separator to the first blank line before the next lyric", () => {
    const lines = parseLrc(
      [
        "[00:10.000]current lyric",
        "[00:12.000]",
        "[00:14.000]",
        "[00:16.000]next lyric",
      ].join("\n"),
    );

    expect(getInstrumentalSeparatorLineIndex(lines, 3)).toBe(1);
  });

  it("keeps the separator on the lyric line when there is no blank gap", () => {
    const lines = parseLrc(
      ["[00:10.000]current lyric", "[00:16.000]next lyric"].join("\n"),
    );

    expect(getInstrumentalSeparatorLineIndex(lines, 1)).toBe(1);
  });
});

describe("getInstrumentalTargetLineIndex", () => {
  it("matches the next lyric line by interval end timestamp", () => {
    const lines = parseLrc(
      [
        "[01:08.312]In the first",
        "[01:09.314]fire",
        "[01:09.715]",
        "[01:19.591]And if you can find it",
      ].join("\n"),
    );

    expect(
      getInstrumentalTargetLineIndex(lines, {
        start: 69.715,
        end: 79.591,
        duration: 9.876,
        lead_in_start: 78.091,
        next_line_index: 14,
        confidence: 1,
        source: "whisperx_gap",
      }),
    ).toBe(3);
  });

  it("falls back to source line index when timestamp is beyond parsed lines", () => {
    const lines = parseLrc(
      ["[00:10.000]first", "[00:20.000]second"].join("\n"),
    );

    expect(
      getInstrumentalTargetLineIndex(lines, {
        start: 19,
        end: 999,
        duration: 980,
        lead_in_start: 997.5,
        next_line_index: 1,
        confidence: 1,
        source: "whisperx_gap",
      }),
    ).toBe(1);
  });

  it("prefers word timing over line timestamp when they disagree", () => {
    const lines = parseLrc(
      [
        "[01:08.000]In the first fire",
        "[01:15.000]And if you can find it",
        "[01:20.000]Hold it tight",
      ].join("\n"),
    ) as ParsedLrcData["lines"];

    lines[1] = {
      ...lines[1],
      words: [
        {
          word: "And",
          start: 79.591,
          end: 79.671,
          line_index: 14,
        },
      ],
    };

    lines[2] = {
      ...lines[2],
      words: [
        {
          word: "Hold",
          start: 88.424,
          end: 88.704,
          line_index: 16,
        },
      ],
    };

    expect(
      getInstrumentalTargetLineIndex(lines, {
        start: 69.715,
        end: 79.591,
        duration: 9.876,
        lead_in_start: 78.091,
        next_line_index: 14,
        confidence: 1,
        source: "whisperx_gap",
      }),
    ).toBe(1);
  });
});