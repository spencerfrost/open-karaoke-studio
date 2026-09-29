/**
 * StageShellContext - the TV's screen state, and the only way to move between screens.
 *
 * Stage mode is a full-screen app, not a set of routes: the performance screen
 * must stay mounted while someone browses, so transitions are state changes
 * rather than navigations. Components that also run on the phone read this
 * context through `useStageShell()`, which returns null off the stage — that is
 * the seam that lets one component navigate on a phone and switch screens here.
 *
 * **Two contexts, deliberately.** The actions never change identity - nothing
 * that varies, like the queue-derived singer list, is allowed in here; the
 * screen state changes on every transition. Song cards and library rows only ever want
 * the actions, and there are several hundred of them mounted at once — putting
 * both in one value meant every screen change re-rendered the entire library.
 * Read `useStageShell()` for the actions, `useStageScreen()` for the state.
 *
 * A third, `useStageQueue()`, carries the queue for the stage's own chrome (the
 * now-playing bar). It changes on every queue broadcast, so it is kept out of
 * the other two, and the memoized song select screen never reads it.
 */

import { createContext, useContext } from "react";
import type {
  KaraokeQueueItemWithSong,
  SessionTurn,
} from "@/types/KaraokeQueue";
import type { Song } from "@/types/Song";

export type StageScreen =
  | { name: "performance" }
  | { name: "select"; expandArtist?: string }
  | { name: "confirm"; song: Song }
  | { name: "add"; query?: string; browseArtist?: boolean }
  /**
   * Between songs. Entered from `songEnded` rather than a tap, and left when a
   * song starts - the only screen the shell drives itself.
   */
  | { name: "handoff" };

export interface StageShellApi {
  openPerformance: () => void;
  openSelect: (opts?: { expandArtist?: string }) => void;
  openConfirm: (song: Song) => void;
  openAdd: (opts?: { query?: string; browseArtist?: boolean }) => void;
  openHandoff: () => void;
  /**
   * One step back along the select-family screens; ends at the performance
   * screen. After a song has ended, song select leads to the handoff screen
   * when the next singer has a song, and nowhere when they don't.
   */
  back: () => void;
}

export interface StageQueue {
  current: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  turn: SessionTurn;
}

export const StageShellContext = createContext<StageShellApi | null>(null);
export const StageScreenContext = createContext<StageScreen | null>(null);
export const StageQueueContext = createContext<StageQueue | null>(null);

/** The stage shell's actions, or null when not running on the stage. */
export const useStageShell = (): StageShellApi | null =>
  useContext(StageShellContext);

/** The active stage screen. Only the shell's own chrome should need this. */
export const useStageScreen = (): StageScreen | null =>
  useContext(StageScreenContext);

/** The session queue as the shell holds it, or null off the stage. */
export const useStageQueue = (): StageQueue | null =>
  useContext(StageQueueContext);
