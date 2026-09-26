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
import type { Song } from "@/types/Song";

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

/**
 * How far a column's list is scrolled, in pixels: enough to centre the cursor
 * row, but never past either end. At the top of the list the first row sits
 * at the top of the column instead of leaving empty space above the cursor;
 * the same at the bottom. A list shorter than the column never scrolls.
 */
export function listScrollOffset(
  cursor: number,
  count: number,
  rowHeight: number,
  viewportPx: number,
): number {
  const centred = cursor * rowHeight + rowHeight / 2 - viewportPx / 2;
  const max = Math.max(0, count * rowHeight - viewportPx);
  return Math.max(0, Math.min(max, centred));
}

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

// ---------------------------------------------------------------------------
// Artwork. See docs/plans/2026-09-25-stage-wheel-artwork.md.
// ---------------------------------------------------------------------------

/** The artist photo, fetched from Discogs on first ask. Shows have none. */
export const artistImageUrl = (
  artist: Pick<Artist, "name" | "isShow">,
): string | null =>
  artist.isShow
    ? null
    : `/api/artists/image?name=${encodeURIComponent(artist.name)}`;

/**
 * Images for the song card's hero, best first: the video still, then the
 * album cover. The reverse of getArtworkUrl, on purpose: stills cover ~71% of
 * songs and covers ~36%, so leading with the still keeps the cards alike.
 */
export function songHeroSources(
  song: Pick<Song, "id" | "thumbnail" | "videoId" | "albumCoverUrl">,
): string[] {
  const sources: string[] = [];
  if (song.thumbnail) sources.push(`/api/songs/${song.id}/thumbnail`);
  // hqdefault always exists; maxresdefault often doesn't. It is 4:3 with the
  // 16:9 picture letterboxed inside, which a 16:9 cover crop removes.
  if (song.videoId)
    sources.push(`https://img.youtube.com/vi/${song.videoId}/hqdefault.jpg`);
  if (song.albumCoverUrl) sources.push(song.albumCoverUrl);
  return sources;
}

const LEADING_ARTICLE = /^(the|a|an)\s+/i;

/** The letter on a tile standing in for a missing image. "The Cure" → "C". */
export function tileInitial(name: string): string {
  const trimmed = name.trim();
  const filed = trimmed.replace(LEADING_ARTICLE, "") || trimmed;
  return (Array.from(filed)[0] ?? "?").toUpperCase();
}

/** "Artist feat. Guest", from credits the artist string doesn't already name. */
export function songByline(song: Pick<Song, "artist" | "artists">): string {
  const credited = song.artist.toLowerCase();
  const featured = (song.artists ?? [])
    .filter((a) => a.role === "featured")
    .map((a) => a.name)
    .filter((name) => !credited.includes(name.toLowerCase()));
  return featured.length > 0
    ? `${song.artist} feat. ${featured.join(", ")}`
    : song.artist;
}

export type LyricsKind = "word-synced" | "synced" | "plain" | "none";

export function lyricsKind(
  song: Pick<Song, "wordSyncedLyrics" | "syncedLyrics" | "plainLyrics">,
): LyricsKind {
  if (song.wordSyncedLyrics) return "word-synced";
  if (song.syncedLyrics) return "synced";
  if (song.plainLyrics) return "plain";
  return "none";
}

/** "G3–D4", or null unless both ends are known. */
export const vocalRange = (
  song: Pick<Song, "vocalRangeLow" | "vocalRangeHigh">,
): string | null =>
  song.vocalRangeLow && song.vocalRangeHigh
    ? `${song.vocalRangeLow}–${song.vocalRangeHigh}`
    : null;

/** The release year, from `year` or else the start of `releaseDate`. */
export function songYear(
  song: Pick<Song, "year" | "releaseDate">,
): number | null {
  if (song.year) return song.year;
  const fromDate = Number.parseInt(song.releaseDate?.slice(0, 4) ?? "", 10);
  return Number.isFinite(fromDate) && fromDate > 0 ? fromDate : null;
}
