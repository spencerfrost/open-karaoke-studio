import { describe, expect, it } from "vitest";
import {
  SWATCH_COUNT,
  singerSwatchKey,
  swatchDot,
  swatchIndex,
} from "./swatch";

describe("swatchIndex", () => {
  it("keeps a number in range, negatives included", () => {
    expect(swatchIndex(0)).toBe(0);
    expect(swatchIndex(SWATCH_COUNT + 2)).toBe(2);
    expect(swatchIndex(-1)).toBe(SWATCH_COUNT - 1);
  });

  it("gives consecutive numbers different swatches", () => {
    const seen = new Set(
      Array.from({ length: SWATCH_COUNT }, (_, i) => swatchIndex(100 + i)),
    );
    expect(seen.size).toBe(SWATCH_COUNT);
  });

  it("gives a string the same swatch every time", () => {
    expect(swatchIndex("Sam")).toBe(swatchIndex("Sam"));
    expect(swatchIndex("Sam")).toBeGreaterThanOrEqual(0);
    expect(swatchIndex("Sam")).toBeLessThan(SWATCH_COUNT);
  });
});

describe("singerSwatchKey", () => {
  it("uses the roster id, so a renamed or reseated singer keeps their colour", () => {
    expect(swatchDot(singerSwatchKey(7, "Sam"))).toBe(
      swatchDot(singerSwatchKey(7, "Samantha")),
    );
  });

  it("falls back to the name for a song from before the roster", () => {
    expect(singerSwatchKey(null, "Sam")).toBe("Sam");
    expect(singerSwatchKey(undefined, "Sam")).toBe("Sam");
  });
});
