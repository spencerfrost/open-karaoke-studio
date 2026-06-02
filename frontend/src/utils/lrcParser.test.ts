import { attachWordTimestamps, parseLrc, type WordTimestamp } from "./lrcParser";

describe("attachWordTimestamps", () => {
  it("prefers backend line_index over timestamp grouping for synced lines", () => {
    const lines = parseLrc(
      [
        "[00:10.000]first line",
        "[00:12.000]second line starts now",
      ].join("\n"),
    );

    const words: WordTimestamp[] = [
      {
        word: "first",
        start: 10.0,
        end: 10.3,
        line_index: 0,
      },
      {
        word: "line",
        start: 10.4,
        end: 10.8,
        line_index: 0,
      },
      {
        word: "second",
        start: 11.92,
        end: 12.1,
        line_index: 1,
      },
      {
        word: "line",
        start: 12.12,
        end: 12.28,
        line_index: 1,
      },
      {
        word: "starts",
        start: 12.3,
        end: 12.55,
        line_index: 1,
      },
      {
        word: "now",
        start: 12.57,
        end: 12.8,
        line_index: 1,
      },
    ];

    const result = attachWordTimestamps(lines, words);

    expect(result[0].words?.map((word) => word.word)).toEqual(["first", "line"]);
    expect(result[1].words?.map((word) => word.word)).toEqual([
      "second",
      "line",
      "starts",
      "now",
    ]);
  });

  it("falls back to timestamp grouping when line_index cannot be mapped", () => {
    const lines = parseLrc(
      [
        "[00:10.000]first line",
        "[00:12.000]second line",
      ].join("\n"),
    );

    const words: WordTimestamp[] = [
      {
        word: "first",
        start: 10.0,
        end: 10.3,
        line_index: 99,
      },
      {
        word: "second",
        start: 12.05,
        end: 12.3,
        line_index: 99,
      },
    ];

    const result = attachWordTimestamps(lines, words);

    expect(result[0].words?.map((word) => word.word)).toEqual(["first"]);
    expect(result[1].words?.map((word) => word.word)).toEqual(["second"]);
  });

  it("falls back to timestamp grouping when backend line indexes drift after a split segment", () => {
    const lines = parseLrc(
      [
        "[01:24.030]Raichu, Nidoqueen, Bellsprout, Starmie",
        "[01:26.380](-woo! we're at the half way point, dooing great so far!",
        "[01:29.670]-we? what's all this we stuff? i'm doing all the hard work!",
        "[01:32.450]-break time's over.here we go!)",
      ].join("\n"),
    );

    const words: WordTimestamp[] = [
      {
        word: "Raichu,",
        start: 84.171,
        end: 84.5,
        line_index: 0,
      },
      {
        word: "Starmie",
        start: 85.9,
        end: 86.159,
        line_index: 0,
      },
      {
        word: "(-woo!",
        start: 86.38,
        end: 86.5,
        line_index: 1,
      },
      {
        word: "we're",
        start: 86.52,
        end: 86.9,
        line_index: 2,
      },
      {
        word: "at",
        start: 86.91,
        end: 87.1,
        line_index: 2,
      },
      {
        word: "the",
        start: 87.11,
        end: 87.2,
        line_index: 2,
      },
      {
        word: "half",
        start: 87.21,
        end: 87.6,
        line_index: 2,
      },
      {
        word: "way",
        start: 87.61,
        end: 87.9,
        line_index: 2,
      },
      {
        word: "point,",
        start: 87.91,
        end: 88.4,
        line_index: 2,
      },
      {
        word: "dooing",
        start: 88.41,
        end: 89.0,
        line_index: 2,
      },
      {
        word: "great",
        start: 89.01,
        end: 89.3,
        line_index: 2,
      },
      {
        word: "so",
        start: 89.31,
        end: 89.5,
        line_index: 2,
      },
      {
        word: "far!",
        start: 89.51,
        end: 89.67,
        line_index: 2,
      },
      {
        word: "-we?",
        start: 89.67,
        end: 89.75,
        line_index: 3,
      },
    ];

    const result = attachWordTimestamps(lines, words);

    expect(result[1].words?.map((word) => word.word)).toEqual([
      "(-woo!",
      "we're",
      "at",
      "the",
      "half",
      "way",
      "point,",
      "dooing",
      "great",
      "so",
      "far!",
    ]);
    expect(result[2].words?.map((word) => word.word)).toEqual(["-we?"]);
  });
});