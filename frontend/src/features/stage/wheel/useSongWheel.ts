/**
 * useSongWheel - the wheel's state and every move it can make.
 *
 * Stored: which source, which column is at the front. Each source keeps its own
 * cursors (see useAzSource, useRecentSource), so switching away and back lands
 * where you were. This hook is what is the same for all of them: turning,
 * Enter, Back, and the song the cursor rests on for the info card.
 *
 * A source's columns always start with the source column, so column 0 is the
 * list of sources and moving in it swaps the columns to its right at once.
 * Under the sources it has action rows (Add a song), which swap nothing: the
 * cursor can rest on one only while the source column is in front.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Song } from "@/types/Song";
import {
  SONGS_SETTLE_MS,
  useAzSource,
  type AzSource,
  type WheelFocusRequest,
} from "./useAzSource";
import { useRecentSource, type RecentSource } from "./useRecentSource";
import {
  INITIAL_COLUMN,
  INITIAL_SOURCE,
  LETTERS,
  SOURCES,
  SOURCE_ACTIONS,
  SOURCE_ROWS,
  clampIndex,
  columnIndexOf,
  sourceIndexOf,
  type ColumnKind,
  type SourceActionId,
  type SourceDef,
  type SourceId,
} from "./wheelModel";

export type { WheelFocusRequest };

interface UseSongWheelOptions {
  /** From the player's "more by this artist", or a search result. */
  focusArtist?: WheelFocusRequest;
  /** Enter on a song. */
  onPickSong: (song: Song) => void;
  /** Enter on (or a click on) an action row of the source column. */
  onAction: (id: SourceActionId) => void;
  /** Back from any column but the songs. */
  onLeave: () => void;
}

/** One column of the current source, as the component draws it. */
export interface WheelColumnState {
  kind: ColumnKind;
  count: number;
  cursor: number;
}

export interface SongWheel {
  source: SourceDef;
  columns: WheelColumnState[];
  /** The column at the front, as an index into `columns`. */
  col: number;
  az: AzSource;
  recent: RecentSource;
  /** The action row the source column's cursor is on, if it is on one. */
  sourceAction: SourceActionId | null;
  /**
   * The song the cursor last rested on while a song column was in front.
   * Kept while the cursor moves on, so artwork can stay until the next loads.
   */
  settledSong: Song | null;
  /** The cursor has moved off `settledSong` and not rested. */
  songPending: boolean;
  /** ▲▼ in the column at the front, `steps` rows (or letters) at once. */
  move: (dir: -1 | 1, steps?: number) => void;
  /**
   * The scroll wheel over a column: brings it to the front and moves in *it*.
   * Named explicitly because `col` in this render is still the old front
   * column until the switch re-renders.
   */
  scrollColumn: (col: number, dir: -1 | 1, steps: number) => void;
  /** ◀▶. Stops at either end rather than falling through to anything else. */
  turn: (dir: -1 | 1) => void;
  enter: () => void;
  back: () => void;
  /** Bring a column to the front (a click or a scroll over a side column). */
  focusColumn: (col: number) => void;
  /**
   * A click on a row in the front column. A source row switches to it, an
   * action row does its action. A
   * letter or an artist moves to it and on to the next column. A song: the
   * centred one acts like Enter, any other moves to it.
   */
  pickRow: (col: number, index: number) => void;
}

const AZ = SOURCES[sourceIndexOf("az")];
const NO_SONGS: Song[] = [];

export function useSongWheel({
  focusArtist,
  onPickSong,
  onAction,
  onLeave,
}: UseSongWheelOptions): SongWheel {
  const [sourceId, setSourceId] = useState<SourceId>(INITIAL_SOURCE);
  const [colState, setCol] = useState(INITIAL_COLUMN);
  const sourceIndex = sourceIndexOf(sourceId);
  const source = SOURCES[sourceIndex];
  const col = Math.min(colState, source.columns.length - 1);
  const frontKind = source.columns[col];
  // Index into SOURCE_ACTIONS while the cursor rests on an action row. Turning
  // away drops it, so the source column behind shows the source on screen.
  const [actionIndex, setActionIndex] = useState<number | null>(null);
  if (actionIndex !== null && col !== 0) setActionIndex(null);
  const sourceRow =
    actionIndex !== null ? SOURCES.length + actionIndex : sourceIndex;
  const sourceAction =
    actionIndex !== null ? SOURCE_ACTIONS[actionIndex].id : null;

  /** Move the source column's cursor to a row: a source or an action. */
  const setSourceRow = useCallback((row: number) => {
    if (row < SOURCES.length) {
      setSourceId(SOURCES[row].id);
      setActionIndex(null);
    } else {
      setActionIndex(row - SOURCES.length);
    }
  }, []);

  // A requested artist is an A–Z thing, wherever the wheel was.
  const handleFocused = useCallback(() => {
    setSourceId("az");
    setCol(columnIndexOf(AZ, "song"));
  }, []);

  const az = useAzSource({
    focusArtist,
    songFront: sourceId === "az" && frontKind === "song",
    onFocused: handleFocused,
  });
  // The recent list is fetched the first time it is shown, then kept.
  const [recentSeen, setRecentSeen] = useState(false);
  if (sourceId === "recent" && !recentSeen) setRecentSeen(true);
  const recent = useRecentSource({ enabled: recentSeen });

  const columns = useMemo<WheelColumnState[]>(
    () =>
      source.columns.map((kind): WheelColumnState => {
        switch (kind) {
          case "source":
            return { kind, count: SOURCE_ROWS, cursor: sourceRow };
          case "letter":
            return { kind, count: LETTERS.length, cursor: az.letterIndex };
          case "artist":
            return { kind, count: az.artists.length, cursor: az.artistIndex };
          case "song":
            return { kind, count: az.songs.length, cursor: az.songIndex };
          case "recent":
            return {
              kind,
              count: recent.songs.length,
              cursor: recent.songIndex,
            };
        }
      }),
    [source, sourceRow, az, recent],
  );

  // The song the cursor rests on, for the info card. Only in a song column:
  // anywhere else the card is not showing, so there is nothing to settle.
  const activeSongs: Song[] =
    frontKind === "song"
      ? az.songs
      : frontKind === "recent"
        ? recent.songs
        : NO_SONGS;
  const activeIndex = frontKind === "song" ? az.songIndex : recent.songIndex;
  const cursorSong = activeSongs[activeIndex] ?? null;
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
        ? (activeSongs.find((s) => s.id === settledSongId) ?? null)
        : null,
    [activeSongs, settledSongId],
  );

  const moveIn = useCallback(
    (c: number, dir: -1 | 1, steps: number) => {
      switch (source.columns[c]) {
        case "source":
          // Scrolling a side source column brings it to the front, so landing
          // on an action row here is fine.
          setSourceRow(clampIndex(sourceRow + dir * steps, SOURCE_ROWS));
          break;
        case "letter":
          az.moveIn("letter", dir, steps);
          break;
        case "artist":
          az.moveIn("artist", dir, steps);
          break;
        case "song":
          az.moveIn("song", dir, steps);
          break;
        case "recent":
          recent.move(dir, steps);
          break;
      }
    },
    [source, sourceRow, setSourceRow, az, recent],
  );

  const move = useCallback(
    (dir: -1 | 1, steps: number = 1) => moveIn(col, dir, steps),
    [moveIn, col],
  );

  const scrollColumn = useCallback(
    (c: number, dir: -1 | 1, steps: number) => {
      setCol(c);
      moveIn(c, dir, steps);
    },
    [moveIn],
  );

  const turn = useCallback(
    (dir: -1 | 1) => setCol(clampIndex(col + dir, source.columns.length)),
    [col, source],
  );

  const enter = useCallback(() => {
    if (frontKind === "song" || frontKind === "recent") {
      if (cursorSong) onPickSong(cursorSong);
    } else if (frontKind === "source" && sourceAction) {
      onAction(sourceAction);
    } else if (frontKind === "source" || az.artist) {
      setCol(col + 1);
    }
  }, [
    frontKind,
    cursorSong,
    onPickSong,
    sourceAction,
    onAction,
    az.artist,
    col,
  ]);

  const back = useCallback(() => {
    if (frontKind === "song") setCol(col - 1);
    else onLeave();
  }, [frontKind, col, onLeave]);

  const focusColumn = useCallback((c: number) => setCol(c), []);

  const pickRow = useCallback(
    (c: number, index: number) => {
      if (c !== col) {
        setCol(c);
        return;
      }
      switch (frontKind) {
        case "source":
          if (index < SOURCES.length) setSourceRow(index);
          else onAction(SOURCE_ACTIONS[index - SOURCES.length].id);
          break;
        case "letter": {
          const target = az.firstByLetter[index];
          if (target === undefined || target === -1) return;
          az.setArtistIndex(target);
          setCol(col + 1);
          break;
        }
        case "artist":
          // Any artist, centred or not: a click means "show me their songs",
          // so it doesn't take a second click to get there.
          az.setArtistIndex(index);
          setCol(col + 1);
          break;
        case "song":
          if (index === az.songIndex) enter();
          else az.setSongIndex(clampIndex(index, az.songs.length));
          break;
        case "recent":
          if (index === recent.songIndex) enter();
          else recent.setSongIndex(index);
          break;
      }
    },
    [col, frontKind, setSourceRow, onAction, az, recent, enter],
  );

  return {
    source,
    columns,
    col,
    az,
    recent,
    sourceAction,
    settledSong,
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
