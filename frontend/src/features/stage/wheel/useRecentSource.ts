/**
 * useRecentSource - the Recently added source: the last songs added, newest
 * first, in one column.
 *
 * The cursor rests on a song, not a row number, so a song added while someone
 * browses does not push their cursor onto its neighbour. The exception is the
 * top row: a cursor there stays there, so opening the list always shows what
 * is newest.
 */

import { useCallback, useMemo, useState } from "react";
import { useSongs } from "@/hooks/api/useSongs";
import type { Song } from "@/types/Song";
import { clampIndex } from "./wheelModel";

/** How many of the newest songs the list holds. */
const RECENT_COUNT = 100;
const RECENT_PARAMS = {
  limit: String(RECENT_COUNT),
  sort_by: "date_added",
  direction: "desc",
};

export interface RecentSource {
  songs: Song[];
  isLoading: boolean;
  error: unknown;
  songIndex: number;
  move: (dir: -1 | 1, steps: number) => void;
  setSongIndex: (index: number) => void;
}

interface UseRecentSourceOptions {
  /** Whether the list is showing; nothing is fetched until it first is. */
  enabled: boolean;
}

export function useRecentSource({
  enabled,
}: UseRecentSourceOptions): RecentSource {
  const { useSongs: useSongsQuery } = useSongs();
  const query = useSongsQuery(RECENT_PARAMS, { enabled });
  const songs = useMemo<Song[]>(() => query.data ?? [], [query.data]);

  // Null is the top row, whatever song that is today.
  const [cursorId, setCursorId] = useState<string | null>(null);
  const found =
    cursorId === null ? 0 : songs.findIndex((s) => s.id === cursorId);
  // A song that has gone (deleted, or failed) lets go of the cursor.
  const songIndex = clampIndex(Math.max(0, found), Math.max(1, songs.length));

  const setSongIndex = useCallback(
    (index: number) => {
      const i = clampIndex(index, songs.length);
      setCursorId(i === 0 ? null : (songs[i]?.id ?? null));
    },
    [songs],
  );

  const move = useCallback(
    (dir: -1 | 1, steps: number) => {
      if (songs.length > 0) setSongIndex(songIndex + dir * steps);
    },
    [songs.length, songIndex, setSongIndex],
  );

  return {
    songs,
    isLoading: query.isLoading,
    error: query.error,
    songIndex,
    move,
    setSongIndex,
  };
}
