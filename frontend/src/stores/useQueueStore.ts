import { create } from "zustand";
import { QueueItem, QueueItemWithSong } from "../types/Queue";
import { Song } from "../types/Song";

interface QueueState {
  items: QueueItemWithSong[];
  currentItem: QueueItemWithSong | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setQueue: (items: QueueItemWithSong[]) => void;
  addToQueue: (item: QueueItemWithSong) => void;
  removeFromQueue: (id: string) => void;
  reorderQueue: (items: QueueItemWithSong[]) => void;
  setCurrentItem: (item: QueueItemWithSong | null) => void;
  nextItem: () => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

// Helper function to build QueueItemWithSong (kept from original implementation)
export const buildQueueItemWithSong = (
  item: QueueItem,
  songs: Song[],
): QueueItemWithSong | null => {
  const song = songs.find((s) => s.id === item.songId);
  if (!song) return null;

  return {
    ...item,
    song,
  };
};

// The Zustand store - equivalent to the previous Context + Reducer combination
export const useQueueStore = create<QueueState>((set) => ({
  // Initial state
  items: [],
  currentItem: null,
  isLoading: false,
  error: null,

  // Actions - directly equivalent to your reducer cases
  setQueue: (items) => set({ items }),

  addToQueue: (item) =>
    set((state) => ({
      items: [...state.items, item],
    })),

  removeFromQueue: (id) =>
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
    })),

  reorderQueue: (items) => set({ items }),

  setCurrentItem: (currentItem) => set({ currentItem }),

  nextItem: () =>
    set((state) => {
      if (state.items.length === 0) {
        return { currentItem: null };
      }

      const nextItem = state.items[0];
      return {
        currentItem: nextItem,
        items: state.items.slice(1),
      };
    }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
