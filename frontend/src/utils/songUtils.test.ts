import { getPreviewStartSeconds } from "./songUtils";

const WINDOW = 30;

describe("getPreviewStartSeconds", () => {
  it("starts 30% into a normal-length song", () => {
    expect(getPreviewStartSeconds(200, WINDOW)).toBe(60);
  });

  it("falls back to the start when the duration is unknown", () => {
    expect(getPreviewStartSeconds(undefined, WINDOW)).toBe(0);
  });

  it("falls back to the start for a non-finite or non-positive duration", () => {
    expect(getPreviewStartSeconds(NaN, WINDOW)).toBe(0);
    expect(getPreviewStartSeconds(Infinity, WINDOW)).toBe(0);
    expect(getPreviewStartSeconds(0, WINDOW)).toBe(0);
    expect(getPreviewStartSeconds(-10, WINDOW)).toBe(0);
  });

  it("backs off so a full preview window still fits before the end", () => {
    // 30% of 40s would be 12s, leaving only 28s — clamp to 40 - 30 - 2 = 8s
    expect(getPreviewStartSeconds(40, WINDOW)).toBe(8);
  });

  it("never returns a negative offset for songs shorter than the window", () => {
    expect(getPreviewStartSeconds(15, WINDOW)).toBe(0);
  });
});
