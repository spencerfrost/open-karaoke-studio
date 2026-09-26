/**
 * wheelModel - the song wheel's rules, with no React in them.
 *
 * Three columns (letter → artist → song) on a cylinder. The part worth keeping
 * out of components is the cursor: **the letter column has no cursor of its
 * own.** It is read off the artist cursor every time, so sitting on Fleetwood
 * Mac and turning left always lands on F. Two stored cursors would disagree
 * the first time one of them scrolled without the other.
 *
 * See docs/plans/2026-09-25-stage-song-wheel.md.
 */

import type { Artist } from "@/hooks/api/useArtists";

/** Every letter, always, so the column's geometry never shifts. */
export const LETTERS = ["#", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"] as const;

export const COLUMN = { letter: 0, artist: 1, song: 2 } as const;
export type ColumnIndex = 0 | 1 | 2;

/** Widths in design pixels, on the 1600×900 frame the wheel is scaled from. */
export const COLUMN_WIDTHS = [130, 560, 620] as const;
export const ROW_HEIGHTS = [72, 64, 66] as const;

/**
 * Starting values from the prototype. The plan says to tune these on the real
 * TV before treating them as settled, so they live in one place.
 */
export const WHEEL_TUNING = {
  /** Space between neighbouring columns, measured along the curve. */
  gapPx: 110,
  radiusPx: 1100,
  turnMs: 320,
  turnEasing: "cubic-bezier(.2,.8,.25,1)",
  /** Opacity one step back from the front; squared per extra step. */
  sideBrightness: 0.45,
  /** Held ▲▼: delay before repeating, then a ramp from 8 to this, rows/sec. */
  holdDelayMs: 350,
  holdStartRate: 8,
  holdTopRate: 36,
  holdRampMs: 1100,
  /** Plain one-row scroll animation, shortened while a key is held. */
  scrollMs: 160,
} as const;

export interface WheelArtist extends Artist {
  /** Index into LETTERS. */
  letterIndex: number;
}

const letterIndexOf = (firstLetter: string): number => {
  const i = LETTERS.indexOf(
    firstLetter.toUpperCase() as (typeof LETTERS)[number],
  );
  return i === -1 ? 0 : i;
};

/**
 * The artist list in wheel order.
 *
 * Grouped by letter first, then in the order the list arrived (already sorted
 * by filing name). The server decides the letter; grouping here guarantees
 * each letter's artists are contiguous even where the two sorts disagree about
 * a character, which the letter jump depends on.
 */
export function toWheelArtists(artists: Artist[]): WheelArtist[] {
  return artists
    .map((artist, order) => ({
      artist: { ...artist, letterIndex: letterIndexOf(artist.firstLetter) },
      order,
    }))
    .sort(
      (a, b) =>
        a.artist.letterIndex - b.artist.letterIndex || a.order - b.order,
    )
    .map(({ artist }) => artist);
}

/** For each letter, the index of its first artist, or -1 when it has none. */
export function firstArtistByLetter(artists: WheelArtist[]): number[] {
  const first = LETTERS.map(() => -1);
  artists.forEach((artist, i) => {
    if (first[artist.letterIndex] === -1) first[artist.letterIndex] = i;
  });
  return first;
}

/**
 * The artist a letter move lands on: the first artist of the next letter in
 * `dir` that has any. Empty letters are skipped. Null at either end.
 */
export function stepLetter(
  artistIndex: number,
  dir: -1 | 1,
  artists: WheelArtist[],
  firstByLetter: number[],
): number | null {
  const current = artists[artistIndex]?.letterIndex ?? 0;
  for (let l = current + dir; l >= 0 && l < LETTERS.length; l += dir) {
    if (firstByLetter[l] !== -1) return firstByLetter[l];
  }
  return null;
}

export const clampIndex = (i: number, length: number): number =>
  Math.max(0, Math.min(length - 1, i));

/** A stable identity for an artist row; shows and artists can share a name. */
export const artistKey = (artist: Pick<Artist, "name" | "isShow">): string =>
  `${artist.isShow ? "show" : "artist"}:${artist.name}`;

/**
 * Where each column sits on the cylinder, in degrees, with artists at 0.
 *
 * Neighbours are spaced by their real widths plus the gap, measured along the
 * curve, so the narrow letter column sits close to the artists instead of
 * taking an equal slice of the circle.
 */
export function columnSeats(
  radiusPx: number = WHEEL_TUNING.radiusPx,
  gapPx: number = WHEEL_TUNING.gapPx,
): [number, number, number] {
  const deg = (px: number) => (px / radiusPx) * (180 / Math.PI);
  const [letterW, artistW, songW] = COLUMN_WIDTHS;
  return [
    -deg(letterW / 2 + artistW / 2 + gapPx),
    0,
    deg(artistW / 2 + songW / 2 + gapPx),
  ];
}

/** Opacity for a column `steps` away from the front: compounds per step. */
export const columnBrightness = (steps: number): number =>
  Math.pow(WHEEL_TUNING.sideBrightness, steps);

/**
 * Rows per second after holding ▲▼ for `heldMs` past the first repeat: a
 * linear climb from the start rate to the top rate over the ramp.
 */
export function holdRate(heldMs: number): number {
  const { holdStartRate, holdTopRate, holdRampMs } = WHEEL_TUNING;
  const t = Math.min(1, Math.max(0, heldMs) / holdRampMs);
  return holdStartRate + t * (holdTopRate - holdStartRate);
}
