/**
 * wheelModel - the song wheel's rules, with no React in them.
 *
 * Columns on a cylinder, in groups called sources. Every source starts with
 * the source column (the list of sources); Artists A–Z follows it with letter
 * → artist → song, Recently added with one list of songs. The part worth
 * keeping out of components is the A–Z cursor: **the letter column has no
 * cursor of its own.** It is read off the artist cursor every time, so sitting
 * on Fleetwood Mac and turning left always lands on F. Two stored cursors
 * would disagree the first time one of them scrolled without the other.
 */

import type { Artist } from "@/hooks/api/useArtists";
import type { Song } from "@/types/Song";
import type { ArtSource } from "./WheelArtwork";

/** Every letter, always, so the column's geometry never shifts. */
export const LETTERS = ["#", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"] as const;

export type ColumnKind = "source" | "letter" | "artist" | "song" | "recent";

export interface ColumnSpec {
  /** Design pixels, on the 1600×900 frame the wheel is scaled from. */
  width: number;
  rowHeight: number;
  /** Pixels from the top of the column where its list starts, below its
   *  header (the songs heading has the artist photo in it). */
  listTop: number;
  /** Never turned to the front: it grows in place while active, and the ring
   *  turns to the next column on its right instead. */
  staysPut?: boolean;
  /** Hidden once two steps behind the front, where it would show through the
   *  columns between. */
  narrow?: boolean;
}

export const COLUMN_SPECS: Record<ColumnKind, ColumnSpec> = {
  // In the middle, the first column had nothing to its left but empty space.
  source: { width: 300, rowHeight: 72, listTop: 60, staysPut: true },
  letter: {
    width: 130,
    rowHeight: 72,
    listTop: 60,
    staysPut: true,
    narrow: true,
  },
  artist: { width: 560, rowHeight: 64, listTop: 60 },
  song: { width: 620, rowHeight: 66, listTop: 128 },
  recent: { width: 620, rowHeight: 84, listTop: 60 },
};

export type SourceId = "az" | "recent";

export interface SourceDef {
  id: SourceId;
  label: string;
  /** Left to right. The source column is always first. */
  columns: readonly ColumnKind[];
}

export const SOURCES: readonly SourceDef[] = [
  {
    id: "az",
    label: "Artists A–Z",
    columns: ["source", "letter", "artist", "song"],
  },
  { id: "recent", label: "Recently added", columns: ["source", "recent"] },
];

export type SourceActionId = "add";

/**
 * Rows under the sources in the source column that do something instead of
 * opening a list. They have no columns of their own: while the cursor rests
 * on one, the source it came from stays showing to the right.
 */
export const SOURCE_ACTIONS: readonly { id: SourceActionId; label: string }[] =
  [{ id: "add", label: "Add a song" }];

/** Rows in the source column: every source, then every action. */
export const SOURCE_ROWS = SOURCES.length + SOURCE_ACTIONS.length;

/** The source the wheel opens on, with its artists in front. */
export const INITIAL_SOURCE: SourceId = "az";
export const INITIAL_COLUMN = 2;

export const sourceIndexOf = (id: SourceId): number =>
  SOURCES.findIndex((s) => s.id === id);

/** Position of a column kind within a source, or -1 when it has none. */
export const columnIndexOf = (source: SourceDef, kind: ColumnKind): number =>
  source.columns.indexOf(kind);

/** What ▲▼ and Enter do in each column, for the legend. */
export const COLUMN_LEGEND: Record<
  ColumnKind,
  { move: string; enter: string }
> = {
  source: { move: "Pick a list", enter: "Open list" },
  // ...unless the cursor is on an action row, whose Enter is its own label.
  letter: { move: "Jump letter", enter: "Go to artists" },
  artist: { move: "Browse artists", enter: "See songs" },
  song: { move: "Browse songs", enter: "Pick song" },
  recent: { move: "Browse songs", enter: "Pick song" },
};

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
  /**
   * Mouse-wheel events closer together than this are one gesture, and stay
   * on the column the gesture started on (see routeWheelScroll).
   */
  scrollGestureGapMs: 250,
  /** A column that stays put grows this much while active instead of turning
   *  to the front. */
  inPlaceActiveScale: 1.15,
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

/**
 * A stable identity for an artist row; shows and artists can share a name.
 * Artists go by id, which survives a rename; shows' ids are made up per list.
 */
export const artistKey = (
  artist: Pick<Artist, "id" | "name" | "isShow">,
): string => (artist.isShow ? `show:${artist.name}` : `artist:${artist.id}`);

/**
 * Where each column of a source sits on the cylinder, in degrees, with the
 * source column at 0.
 *
 * Neighbours are spaced by their real widths plus the gap, measured along the
 * curve, so a narrow column sits close to its neighbour instead of taking an
 * equal slice of the circle. The source column is the same place in every
 * source, so it stays put when the source changes.
 */
export function columnSeats(
  kinds: readonly ColumnKind[],
  radiusPx: number = WHEEL_TUNING.radiusPx,
  gapPx: number = WHEEL_TUNING.gapPx,
): number[] {
  const deg = (px: number) => (px / radiusPx) * (180 / Math.PI);
  let centre = 0;
  return kinds.map((kind, i) => {
    if (i > 0) {
      centre +=
        COLUMN_SPECS[kinds[i - 1]].width / 2 +
        gapPx +
        COLUMN_SPECS[kind].width / 2;
    }
    return deg(centre);
  });
}

/**
 * The ring's angle with column `col` active. The source and letter columns
 * never turn the ring: bringing either to the middle shoved the whole wheel
 * into the left half of the screen. The ring turns to the first column on
 * their right that doesn't stay put, and they grow in place instead.
 */
export function ringAngleFor(
  col: number,
  seats: readonly number[],
  kinds: readonly ColumnKind[],
): number {
  let front = col;
  while (front < kinds.length - 1 && COLUMN_SPECS[kinds[front]].staysPut)
    front++;
  return -seats[front];
}

/** One mouse-wheel gesture: the column it went to, and its last event. */
export interface WheelScrollLock {
  col: number;
  at: number;
}

/**
 * Which column a mouse-wheel event scrolls, given the column under the
 * pointer (null over empty space).
 *
 * A scroll over a side column brings it to the front, which turns the ring
 * under a pointer that hasn't moved: the rest of the same flick would land on
 * whatever turned in under it - another column, or empty space where nothing
 * scrolls at all. Instead, events that keep arriving less than `gapMs` apart
 * are one gesture and all go to the column it started on, wherever the
 * pointer now is. A pause starts a new gesture over whatever is under the
 * pointer; over empty space, none starts.
 *
 * `started` marks the first event of a gesture.
 */
export function routeWheelScroll(
  lock: WheelScrollLock | null,
  hovered: number | null,
  now: number,
  gapMs: number = WHEEL_TUNING.scrollGestureGapMs,
):
  | { target: number; lock: WheelScrollLock; started: boolean }
  | { target: null; lock: null; started: false } {
  if (lock && now - lock.at < gapMs) {
    return {
      target: lock.col,
      lock: { col: lock.col, at: now },
      started: false,
    };
  }
  if (hovered === null) return { target: null, lock: null, started: false };
  return { target: hovered, lock: { col: hovered, at: now }, started: true };
}

/** Opacity for a column `steps` away from the front: compounds per step. */
export const columnBrightness = (steps: number): number =>
  Math.pow(WHEEL_TUNING.sideBrightness, steps);

/**
 * Whether a column `steps` away from the front is not drawn at all. A narrow
 * column turns in behind the ones in front of it and would show through; any
 * column this far back is too dim to read anyway.
 */
export const isColumnHidden = (kind: ColumnKind, steps: number): boolean =>
  steps >= 3 || (!!COLUMN_SPECS[kind].narrow && steps >= 2);

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
// Artwork.
// ---------------------------------------------------------------------------

/** The artist photo, fetched from Discogs on first ask. Shows have none. */
export const artistImageUrl = (
  artist: Pick<Artist, "id" | "isShow">,
): string | null => (artist.isShow ? null : `/api/artists/${artist.id}/image`);

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

/**
 * The song's video is an album track upload: its still is the album cover
 * between two plain bars, so a still and a cover side by side are one picture.
 */
export const stillIsCover = (song: Pick<Song, "videoIsAlbumArt">): boolean =>
  song.videoIsAlbumArt === true;

/**
 * Images for the cover alone, best first: the album cover, then the middle of
 * the video still, which for an album track upload is the same cover.
 */
export function songCoverSources(
  song: Pick<Song, "id" | "thumbnail" | "videoId" | "albumCoverUrl">,
): ArtSource[] {
  const sources: ArtSource[] = [];
  if (song.albumCoverUrl) sources.push(song.albumCoverUrl);
  if (song.thumbnail)
    sources.push({ url: `/api/songs/${song.id}/thumbnail`, videoMiddle: true });
  if (song.videoId)
    sources.push({
      url: `https://img.youtube.com/vi/${song.videoId}/hqdefault.jpg`,
      videoMiddle: true,
    });
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
/** Who a song is by, from its primary credits ("Rihanna", "A & B"). */
export function primaryArtists(song: Pick<Song, "artist" | "artists">): string {
  const primaries = (song.artists ?? [])
    .filter((a) => a.role === "primary")
    .map((a) => a.name);
  return primaries.length > 0 ? primaries.join(" & ") : song.artist;
}

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
