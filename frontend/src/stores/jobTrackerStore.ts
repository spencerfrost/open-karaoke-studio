import { create } from "zustand";
import type { SongProcessingStatus } from "@/types/Song";
import {
  mergeJobs,
  pruneFinished,
  type TrackedSongs,
} from "@/features/songs/processing/jobTimeline";

/**
 * The jobs feed folded into one timeline per song (see jobTimeline). Holds
 * everyone's songs, each with the opaque tag of the session that added it;
 * views filter by their own session's tag, so nothing here is per-session.
 * Fed once, at app level, by useJobsSync.
 */
interface JobTrackerState {
  songs: TrackedSongs;
  sync: (jobs: SongProcessingStatus[]) => void;
  /** Drop finished songs past their TTL; run on a timer by useJobsSync. */
  prune: () => void;
  /** Drop a finished song's row, e.g. once it has been sung. */
  dismiss: (songId: string) => void;
  /**
   * Drop the rows of finished songs that are now in the queue, however they
   * got there. Songs still in the pipeline keep their rows.
   */
  dismissFinished: (songIds: Iterable<string>) => void;
}

export const useJobTrackerStore = create<JobTrackerState>((set) => ({
  songs: {},
  sync: (jobs) =>
    set((state) => ({ songs: mergeJobs(state.songs, jobs, Date.now()) })),
  prune: () =>
    set((state) => {
      const songs = pruneFinished(state.songs, Date.now());
      return songs === state.songs ? state : { songs };
    }),
  dismiss: (songId) =>
    set((state) => {
      if (!state.songs[songId]) return state;
      const songs = { ...state.songs };
      delete songs[songId];
      return { songs };
    }),
  dismissFinished: (songIds) =>
    set((state) => {
      let songs: TrackedSongs | null = null;
      for (const songId of songIds) {
        if (state.songs[songId]?.finishedAt == null) continue;
        songs ??= { ...state.songs };
        delete songs[songId];
      }
      return songs ? { songs } : state;
    }),
}));
