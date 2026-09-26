/**
 * useSongWheel - the wheel's state and every move it can make.
 *
 * Stored: which column is at the front, which artist, which song. Derived:
 * everything else, the letter cursor above all (see wheelModel). The artist is
 * stored by identity rather than index, so a library refetch that inserts a
 * new artist above the cursor does not quietly move it onto someone else.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useArtists } from "@/hooks/api/useArtists";
import {
  useInfiniteArtistSongs,
  useInfiniteShowSongs,
} from "@/hooks/api/useArtistSongs";
import type { Song } from "@/types/Song";
import {
  COLUMN,
  artistKey,
  clampIndex,
  firstArtistByLetter,
  stepLetter,
  toWheelArtists,
  type ColumnIndex,
  type WheelArtist,
} from "./wheelModel";

/**
 * How long a cursor has to rest before anything is fetched for it: an
 * artist's songs, an artist photo, a song's artwork. Holding ▼ passes 30 rows
 * a second; fetching for each one on the way past would be 30 requests for
 * things nobody saw - and for artist photos, 30 Discogs lookups against a
 * limit of 60 a minute.
 */
const SONGS_SETTLE_MS = 150;
/** Songs per request. Almost every artist fits in one page. */
const SONGS_PAGE_SIZE = 200;
/** Fetch the next page when the song cursor gets this close to the end. */
const SONGS_PREFETCH_ROWS = 10;

/**
 * "Take me to this artist, songs in front." An object so that asking for the
 * same artist twice is still two requests: each new object is handled once.
 */
export interface WheelFocusRequest {
  name: string;
  isShow?: boolean;
}

interface UseSongWheelOptions {
  /** From the player's "more by this artist", or a search result. */
  focusArtist?: WheelFocusRequest;
  /** Enter on a song. */
  onPickSong: (song: Song) => void;
  /** Back from the letter or artist column. */
  onLeave: () => void;
}

export interface SongWheel {
  isLoading: boolean;
  error: unknown;
  artists: WheelArtist[];
  firstByLetter: number[];
  col: ColumnIndex;
  artistIndex: number;
  artist: WheelArtist | null;
  letterIndex: number;
  songs: Song[];
  songsLoading: boolean;
  songIndex: number;
  /** The artist the cursor last rested on; lags `artist` while it moves. */
  settledArtist: WheelArtist | null;
  /**
   * The song the cursor last rested on while the song column was in front.
   * Kept while the cursor moves on, so artwork can stay until the next loads.
   */
  settledSong: Song | null;
  /** The cursor has moved off `settledArtist` / `settledSong` and not rested. */
  artistPending: boolean;
  songPending: boolean;
  /** ▲▼ in the column at the front, `steps` rows (or letters) at once. */
  move: (dir: -1 | 1, steps?: number) => void;
  /**
   * The scroll wheel over a column: brings it to the front and moves in *it*.
   * Named explicitly because `col` in this render is still the old front
   * column until the switch re-renders.
   */
  scrollColumn: (col: ColumnIndex, dir: -1 | 1, steps: number) => void;
  /** ◀▶. Stops at either end rather than falling through to anything else. */
  turn: (dir: -1 | 1) => void;
  enter: () => void;
  back: () => void;
  /** Bring a column to the front (a click or a scroll over a side column). */
  focusColumn: (col: ColumnIndex) => void;
  /** A click on a row: the centred row acts like Enter, any other moves to it. */
  pickRow: (col: ColumnIndex, index: number) => void;
}

export function useSongWheel({
  focusArtist,
  onPickSong,
  onLeave,
}: UseSongWheelOptions): SongWheel {
  const { artists: rawArtists, isLoading, error } = useArtists();
  const artists = useMemo(() => toWheelArtists(rawArtists), [rawArtists]);
  const firstByLetter = useMemo(() => firstArtistByLetter(artists), [artists]);
  const indexByKey = useMemo(
    () => new Map(artists.map((a, i) => [artistKey(a), i])),
    [artists],
  );

  const [col, setCol] = useState<ColumnIndex>(COLUMN.artist);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [songIndex, setSongIndex] = useState(0);

  const artistIndex =
    selectedKey !== null ? (indexByKey.get(selectedKey) ?? 0) : 0;
  const artist = artists[artistIndex] ?? null;
  const letterIndex = artist?.letterIndex ?? 0;
  const currentKey = artist ? artistKey(artist) : null;

  const setArtistIndex = useCallback(
    (i: number) => {
      const next = artists[clampIndex(i, artists.length)];
      if (!next) return;
      const key = artistKey(next);
      setSelectedKey(key);
      if (key !== currentKey) setSongIndex(0);
    },
    [artists, currentKey],
  );

  // Land on a requested artist with their songs in front - once per request,
  // not on every render after it, or the cursor could never leave. Waits for
  // the library to load rather than dropping a request that arrived first.
  const handledFocus = useRef<WheelFocusRequest | undefined>(undefined);
  useEffect(() => {
    if (!focusArtist || handledFocus.current === focusArtist) return;
    if (artists.length === 0) return;
    handledFocus.current = focusArtist;
    const target = artists.find(
      (a) => a.name === focusArtist.name && !!a.isShow === !!focusArtist.isShow,
    );
    if (!target) return;
    setSelectedKey(artistKey(target));
    setSongIndex(0);
    setCol(COLUMN.song);
  }, [focusArtist, artists]);

  // Songs for the artist the cursor has settled on - except once the song
  // column is in front, when waiting would only make Enter feel slow.
  const [settledKey, setSettledKey] = useState<string | null>(null);
  useEffect(() => {
    if (col === COLUMN.song) {
      setSettledKey(currentKey);
      return;
    }
    const timer = setTimeout(() => setSettledKey(currentKey), SONGS_SETTLE_MS);
    return () => clearTimeout(timer);
  }, [currentKey, col]);

  const settledArtist =
    (settledKey !== null ? artists[indexByKey.get(settledKey) ?? -1] : null) ??
    null;
  const songsArtist = settledArtist;
  const artistSongs = useInfiniteArtistSongs(
    songsArtist?.name ?? "",
    SONGS_PAGE_SIZE,
    { enabled: !!songsArtist && !songsArtist.isShow },
  );
  const showSongs = useInfiniteShowSongs(
    songsArtist?.name ?? "",
    SONGS_PAGE_SIZE,
    { enabled: !!songsArtist?.isShow },
  );
  const songsQuery = songsArtist?.isShow ? showSongs : artistSongs;
  // Until the cursor settles the column shows nothing rather than the previous
  // artist's songs under the new artist's name.
  const songsAreCurrent = songsArtist !== null && settledKey === currentKey;
  const songs = useMemo(
    () => (songsAreCurrent ? songsQuery.songs : []),
    [songsAreCurrent, songsQuery.songs],
  );
  const songsLoading = !songsAreCurrent || songsQuery.isLoading;
  const clampedSongIndex = clampIndex(songIndex, Math.max(1, songs.length));

  // The song the cursor rests on, for the info card. Only in the song column:
  // anywhere else the card is not showing, so there is nothing to settle.
  const cursorSong =
    col === COLUMN.song ? (songs[clampedSongIndex] ?? null) : null;
  const cursorSongId = cursorSong?.id ?? null;
  const [settledSongId, setSettledSongId] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(
      () => setSettledSongId(cursorSongId),
      SONGS_SETTLE_MS,
    );
    return () => clearTimeout(timer);
  }, [cursorSongId]);
  const settledSong = useMemo(
    () =>
      settledSongId !== null
        ? (songs.find((s) => s.id === settledSongId) ?? null)
        : null,
    [songs, settledSongId],
  );

  const { hasNextPage, isFetchingNextPage, fetchNextPage } = songsQuery;
  useEffect(() => {
    if (
      hasNextPage &&
      !isFetchingNextPage &&
      clampedSongIndex >= songs.length - SONGS_PREFETCH_ROWS
    ) {
      fetchNextPage();
    }
  }, [
    clampedSongIndex,
    songs.length,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  ]);

  const moveIn = useCallback(
    (c: ColumnIndex, dir: -1 | 1, steps: number) => {
      if (c === COLUMN.letter) {
        let target = artistIndex;
        for (let n = 0; n < steps; n++) {
          const next = stepLetter(target, dir, artists, firstByLetter);
          if (next === null) break;
          target = next;
        }
        if (target !== artistIndex) setArtistIndex(target);
      } else if (c === COLUMN.artist) {
        setArtistIndex(artistIndex + dir * steps);
      } else if (songs.length > 0) {
        setSongIndex(clampIndex(clampedSongIndex + dir * steps, songs.length));
      }
    },
    [
      artistIndex,
      artists,
      firstByLetter,
      setArtistIndex,
      songs.length,
      clampedSongIndex,
    ],
  );

  const move = useCallback(
    (dir: -1 | 1, steps: number = 1) => moveIn(col, dir, steps),
    [moveIn, col],
  );

  const scrollColumn = useCallback(
    (c: ColumnIndex, dir: -1 | 1, steps: number) => {
      setCol(c);
      moveIn(c, dir, steps);
    },
    [moveIn],
  );

  const turn = useCallback((dir: -1 | 1) => {
    setCol((c) => Math.max(0, Math.min(2, c + dir)) as ColumnIndex);
  }, []);

  const enter = useCallback(() => {
    if (col === COLUMN.song) {
      const song = songs[clampedSongIndex];
      if (song) onPickSong(song);
    } else if (artist) {
      setCol((col + 1) as ColumnIndex);
    }
  }, [col, songs, clampedSongIndex, onPickSong, artist]);

  const back = useCallback(() => {
    if (col === COLUMN.song) setCol(COLUMN.artist);
    else onLeave();
  }, [col, onLeave]);

  const focusColumn = useCallback((c: ColumnIndex) => setCol(c), []);

  const pickRow = useCallback(
    (c: ColumnIndex, index: number) => {
      if (c !== col) {
        setCol(c);
        return;
      }
      if (c === COLUMN.letter) {
        const target = firstByLetter[index];
        if (target === undefined || target === -1) return;
        setArtistIndex(target);
        setCol(COLUMN.artist);
      } else if (c === COLUMN.artist) {
        if (index === artistIndex) enter();
        else setArtistIndex(index);
      } else if (index === clampedSongIndex) {
        enter();
      } else {
        setSongIndex(clampIndex(index, songs.length));
      }
    },
    [
      col,
      firstByLetter,
      setArtistIndex,
      artistIndex,
      enter,
      clampedSongIndex,
      songs.length,
    ],
  );

  return {
    isLoading,
    error,
    artists,
    firstByLetter,
    col,
    artistIndex,
    artist,
    letterIndex,
    songs,
    songsLoading,
    songIndex: clampedSongIndex,
    settledArtist,
    settledSong,
    artistPending: settledKey !== currentKey,
    songPending: cursorSongId !== settledSongId,
    move,
    scrollColumn,
    turn,
    enter,
    back,
    focusColumn,
    pickRow,
  };
}
