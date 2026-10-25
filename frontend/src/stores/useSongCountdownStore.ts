/**
 * Song countdown - the 3-2-1 the stage shows before a new song starts.
 *
 * Client-only stage state. Nothing about it is sent to the server: the song
 * isn't playing while the stage counts, and the player state every phone
 * already sees says exactly that.
 *
 * The phases, for anything that wants to follow along (the guided tour):
 * - `idle`: no song is being started.
 * - `waiting`: a new song was asked for, but the count can't run yet: the old
 *   song is still fading out, or another screen is covering the player.
 * - `counting`: the number is on screen. `holding` means the count has reached
 *   1 and is staying there until the audio is ready.
 *
 * The song starts when the count leaves `counting` for `idle` and the player
 * store's `isPlaying` turns true. `useSongStart` drives all of this.
 */

import { create } from "zustand";

/** The count starts here and steps down to 1. */
export const COUNTDOWN_FROM = 3;
/** How long each number is on screen. */
export const COUNTDOWN_STEP_MS = 1000;

export type SongCountdown =
  | { phase: "idle" }
  | { phase: "waiting"; songId: string }
  | {
      phase: "counting";
      songId: string;
      count: number;
      /** The count reached 1 and is holding there until the audio is ready. */
      holding: boolean;
    };

export const IDLE: SongCountdown = { phase: "idle" };

/** A new song was asked for. A later song replaces one still counting. */
export function requestCountdown(
  state: SongCountdown,
  songId: string,
): SongCountdown {
  if (state.phase !== "idle" && state.songId === songId) return state;
  return { phase: "waiting", songId };
}

/** The player has switched to the song and is on screen: start the count. */
export function beginCountdown(
  state: SongCountdown,
  songId: string,
): SongCountdown {
  if (state.phase !== "waiting" || state.songId !== songId) return state;
  return { phase: "counting", songId, count: COUNTDOWN_FROM, holding: false };
}

/** The player was covered mid-count: wait, and count again from the top. */
export function suspendCountdown(state: SongCountdown): SongCountdown {
  if (state.phase !== "counting") return state;
  return { phase: "waiting", songId: state.songId };
}

/**
 * One step of the count. On 1 the number stays put and the count holds:
 * the song starts as soon as it's ready, never before.
 */
export function tickCountdown(state: SongCountdown): SongCountdown {
  if (state.phase !== "counting" || state.holding) return state;
  if (state.count > 1) return { ...state, count: state.count - 1 };
  return { ...state, holding: true };
}

/** The count is done and the audio is ready: the song can start. */
export function isReadyToStart(
  state: SongCountdown,
  songId: string | null,
  audioReady: boolean,
): boolean {
  return (
    state.phase === "counting" &&
    state.holding &&
    state.songId === songId &&
    audioReady
  );
}

interface SongCountdownStore {
  countdown: SongCountdown;
  request: (songId: string) => void;
  begin: (songId: string) => void;
  suspend: () => void;
  tick: () => void;
  /** Back to idle: the song started, failed, or is no longer wanted. */
  clear: () => void;
}

export const useSongCountdownStore = create<SongCountdownStore>((set) => ({
  countdown: IDLE,
  request: (songId) =>
    set((s) => ({ countdown: requestCountdown(s.countdown, songId) })),
  begin: (songId) =>
    set((s) => ({ countdown: beginCountdown(s.countdown, songId) })),
  suspend: () => set((s) => ({ countdown: suspendCountdown(s.countdown) })),
  tick: () => set((s) => ({ countdown: tickCountdown(s.countdown) })),
  clear: () => set({ countdown: IDLE }),
}));
