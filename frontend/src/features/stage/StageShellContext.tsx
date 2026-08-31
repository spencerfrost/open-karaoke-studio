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
 */

import { createContext, useContext } from "react";
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
  /** One step back along the select-family screens; ends at the performance screen. */
  back: () => void;
}

export const StageShellContext = createContext<StageShellApi | null>(null);
export const StageScreenContext = createContext<StageScreen | null>(null);

/** The stage shell's actions, or null when not running on the stage. */
export const useStageShell = (): StageShellApi | null =>
  useContext(StageShellContext);

/** The active stage screen. Only the shell's own chrome should need this. */
export const useStageScreen = (): StageScreen | null =>
  useContext(StageScreenContext);
