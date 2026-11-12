/**
 * useAzSource - the Artists A–Z source: letter, artist and song state.
 *
 * Stored: which artist, which song. Derived: everything else, the letter
 * cursor above all (see wheelModel). The artist is stored by identity rather
 * than index, so a library refetch that inserts a new artist above the cursor
 * does not quietly move it onto someone else.
 *
 * Knows nothing of columns or which one is in front beyond `songFront`; the
 * wheel decides where a move or a click goes next.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useArtists } from "@/hooks/api/useArtists";
import {
  useInfiniteArtistSongs,
  useInfiniteShowSongs,
  type ArtistSong,
} from "@/hooks/api/useArtistSongs";
import {
  artistKey,
  clampIndex,
  firstArtistByLetter,
  stepLetter,
  toWheelArtists,
  type WheelArtist,
} from "./wheelModel";

/**
 * How long a cursor has to rest before anything is fetched for it: an
 * artist's songs, an artist photo, a song's artwork. Holding ▼ passes 30 rows
 * a second; fetching for each one on the way past would be 30 requests for
 * things nobody saw - and for artist photos, 30 Discogs lookups against a
 * limit of 60 a minute.
 */
export const SONGS_SETTLE_MS = 150;
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

export interface AzSource {
  isLoading: boolean;
  error: unknown;
  artists: WheelArtist[];
  firstByLetter: number[];
  artistIndex: number;
  artist: WheelArtist | null;
  letterIndex: number;
  /** Their own songs, then the ones they guest on (`role: "featured"`). */
  songs: ArtistSong[];
  /**
   * Rows in the song column: the songs, then a "Find more from …" row once
   * every page of them is in (the songbook's browse card, as a row). The
   * cursor rests on it like a song; `songIndex === songs.length` is it.
   */
  songRows: number;
  /** The cursor is on the "Find more from …" row. */
  onFindMore: boolean;
  songsLoading: boolean;
  songIndex: number;
  /** The artist the cursor last rested on; lags `artist` while it moves. */
  settledArtist: WheelArtist | null;
  /** The cursor has moved off `settledArtist` and not rested. */
  artistPending: boolean;
  /** ▲▼ in one of this source's columns, `steps` rows (or letters) at once. */
  moveIn: (
    kind: "letter" | "artist" | "song",
    dir: -1 | 1,
    steps: number,
  ) => void;
  /** Move the artist cursor; the song cursor goes back to the top. */
  setArtistIndex: (index: number) => void;
  setSongIndex: (index: number) => void;
}

interface UseAzSourceOptions {
  focusArtist?: WheelFocusRequest;
  /** The song column is in front, so its songs are wanted without a wait. */
  songFront: boolean;
  /** Called once a requested artist has been landed on. */
  onFocused: () => void;
}

export function useAzSource({
  focusArtist,
  songFront,
  onFocused,
}: UseAzSourceOptions): AzSource {
  const { artists: rawArtists, isLoading, error } = useArtists();
  const artists = useMemo(() => toWheelArtists(rawArtists), [rawArtists]);
  const firstByLetter = useMemo(() => firstArtistByLetter(artists), [artists]);
  const indexByKey = useMemo(
    () => new Map(artists.map((a, i) => [artistKey(a), i])),
    [artists],
  );

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
    onFocused();
  }, [focusArtist, artists, onFocused]);

  // Songs for the artist the cursor has settled on - except once the song
  // column is in front, when waiting would only make Enter feel slow.
  const [settledKey, setSettledKey] = useState<string | null>(null);
  useEffect(() => {
    if (songFront) {
      setSettledKey(currentKey);
      return;
    }
    const timer = setTimeout(() => setSettledKey(currentKey), SONGS_SETTLE_MS);
    return () => clearTimeout(timer);
  }, [currentKey, songFront]);

  const settledArtist =
    (settledKey !== null ? artists[indexByKey.get(settledKey) ?? -1] : null) ??
    null;
  const songsArtist = settledArtist;
  const artistSongs = useInfiniteArtistSongs(
    songsArtist && !songsArtist.isShow ? songsArtist.id : null,
    SONGS_PAGE_SIZE,
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
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = songsQuery;
  // Only after the last page: a row that moved down as pages arrived would
  // slide out from under the cursor.
  const songRows =
    songs.length > 0 && !songsLoading && !hasNextPage
      ? songs.length + 1
      : songs.length;
  const clampedSongIndex = clampIndex(songIndex, Math.max(1, songRows));

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
    (kind: "letter" | "artist" | "song", dir: -1 | 1, steps: number) => {
      if (kind === "letter") {
        let target = artistIndex;
        for (let n = 0; n < steps; n++) {
          const next = stepLetter(target, dir, artists, firstByLetter);
          if (next === null) break;
          target = next;
        }
        if (target !== artistIndex) setArtistIndex(target);
      } else if (kind === "artist") {
        setArtistIndex(artistIndex + dir * steps);
      } else if (songRows > 0) {
        setSongIndex(clampIndex(clampedSongIndex + dir * steps, songRows));
      }
    },
    [
      artistIndex,
      artists,
      firstByLetter,
      setArtistIndex,
      songRows,
      clampedSongIndex,
    ],
  );

  return {
    isLoading,
    error,
    artists,
    firstByLetter,
    artistIndex,
    artist,
    letterIndex,
    songs,
    songsLoading,
    songRows,
    onFindMore: songRows > songs.length && clampedSongIndex === songs.length,
    songIndex: clampedSongIndex,
    settledArtist,
    artistPending: settledKey !== currentKey,
    moveIn,
    setArtistIndex,
    setSongIndex,
  };
}
