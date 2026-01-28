import { create } from "zustand";
import { SongProcessingStatus } from "@/types/Song";

interface ProcessingIndicatorsState {
  // Map of song_id -> processing status for O(1) lookups
  processingSongs: Map<string, SongProcessingStatus>;

  // Actions
  setProcessing: (songId: string, status: SongProcessingStatus) => void;
  removeProcessing: (songId: string) => void;
  clearCompleted: () => void;

  // Selectors
  isProcessing: (songId: string) => boolean;
  getProgress: (songId: string) => number | undefined;
  getStatus: (songId: string) => SongProcessingStatus | undefined;
}

export const useProcessingIndicators = create<ProcessingIndicatorsState>(
  (set, get) => ({
    processingSongs: new Map(),

    setProcessing: (songId, status) =>
      set((state) => {
        const newMap = new Map(state.processingSongs);
        newMap.set(songId, status);
        return { processingSongs: newMap };
      }),

    removeProcessing: (songId) =>
      set((state) => {
        const newMap = new Map(state.processingSongs);
        newMap.delete(songId);
        return { processingSongs: newMap };
      }),

    clearCompleted: () =>
      set((state) => {
        const newMap = new Map(state.processingSongs);
        for (const [songId, status] of newMap.entries()) {
          if (status.status === "processed" || status.status === "error") {
            newMap.delete(songId);
          }
        }
        return { processingSongs: newMap };
      }),

    isProcessing: (songId) => get().processingSongs.has(songId),

    getProgress: (songId) => get().processingSongs.get(songId)?.progress,

    getStatus: (songId) => get().processingSongs.get(songId),
  }),
);
