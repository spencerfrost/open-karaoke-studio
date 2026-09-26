import { describe, expect, it } from "vitest";
import type { Artist } from "@/hooks/api/useArtists";
import {
  LETTERS,
  columnBrightness,
  columnSeats,
  firstArtistByLetter,
  holdRate,
  stepLetter,
  toWheelArtists,
  WHEEL_TUNING,
} from "./wheelModel";

const artist = (name: string, firstLetter: string, id = 0): Artist => ({
  id,
  name,
  sortName: name.toLowerCase(),
  songCount: 1,
  firstLetter,
});

const letter = (l: string) => LETTERS.indexOf(l as (typeof LETTERS)[number]);

describe("toWheelArtists", () => {
  it("groups by letter so each letter's artists are contiguous", () => {
    const wheel = toWheelArtists([
      artist("ABBA", "A"),
      artist("Øystein", "#"),
      artist("Beck", "B"),
      artist("3 Doors Down", "#"),
    ]);
    expect(wheel.map((a) => a.name)).toEqual([
      "Øystein",
      "3 Doors Down",
      "ABBA",
      "Beck",
    ]);
  });

  it("files an unknown letter under #", () => {
    expect(toWheelArtists([artist("?", "?")])[0].letterIndex).toBe(0);
  });
});

describe("stepLetter", () => {
  const wheel = toWheelArtists([
    artist("ABBA", "A"),
    artist("Adele", "A"),
    artist("Beck", "B"),
    artist("Dido", "D"),
  ]);
  const first = firstArtistByLetter(wheel);

  it("lands on the first artist of the next letter", () => {
    expect(stepLetter(1, 1, wheel, first)).toBe(2);
  });

  it("skips letters with no artists", () => {
    expect(first[letter("C")]).toBe(-1);
    expect(stepLetter(2, 1, wheel, first)).toBe(3);
  });

  it("goes back to the first artist of the previous letter", () => {
    expect(stepLetter(3, -1, wheel, first)).toBe(2);
    expect(stepLetter(2, -1, wheel, first)).toBe(0);
  });

  it("stops at either end", () => {
    expect(stepLetter(0, -1, wheel, first)).toBeNull();
    expect(stepLetter(3, 1, wheel, first)).toBeNull();
  });
});

describe("geometry", () => {
  it("puts artists at the front, letters left and songs right", () => {
    const [l, a, s] = columnSeats();
    expect(a).toBe(0);
    expect(l).toBeLessThan(0);
    expect(s).toBeGreaterThan(0);
  });

  it("seats the narrow letter column closer than the wide song column", () => {
    const [l, , s] = columnSeats();
    expect(Math.abs(l)).toBeLessThan(Math.abs(s));
  });

  it("compounds dimming per step back", () => {
    expect(columnBrightness(0)).toBe(1);
    expect(columnBrightness(2)).toBeCloseTo(WHEEL_TUNING.sideBrightness ** 2);
  });
});

describe("holdRate", () => {
  it("ramps from the start rate to the top rate and holds there", () => {
    expect(holdRate(-100)).toBe(WHEEL_TUNING.holdStartRate);
    expect(holdRate(0)).toBe(WHEEL_TUNING.holdStartRate);
    expect(holdRate(WHEEL_TUNING.holdRampMs)).toBe(WHEEL_TUNING.holdTopRate);
    expect(holdRate(10_000)).toBe(WHEEL_TUNING.holdTopRate);
  });
});
