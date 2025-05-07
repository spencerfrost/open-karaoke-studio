import { create } from "zustand";
import {
  KaraokeQueueItem,
  KaraokeQueueItemWithSong,
} from "../types/KaraokeQueue";
import { Song } from "../types/Song";

interface KaraokeQueueState {
  items: KaraokeQueueItemWithSong[];
  currentSong: KaraokeQueueItemWithSong | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setKaraokeQueue: (items: KaraokeQueueItemWithSong[]) => void;
  addToKaraokeQueue: (item: KaraokeQueueItemWithSong) => void;
  removeFromKaraokeQueue: (id: string) => void;
  reorderKaraokeQueue: (items: KaraokeQueueItemWithSong[]) => void;
  setCurrentSong: (item: KaraokeQueueItemWithSong | null) => void;
  nextSong: () => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

// Helper function to build KaraokeQueueItemWithSong (kept from original implementation)
export const buildKaraokeQueueItemWithSong = (
  item: KaraokeQueueItem,
  songs: Song[]
): KaraokeQueueItemWithSong | null => {
  const song = songs.find((s) => s.id === item.songId);
  if (!song) return null;

  return {
    ...item,
    song,
  };
};

export const useKaraokeQueueStore = create<KaraokeQueueState>((set) => ({
  items: [],
  currentSong: null,
  isLoading: false,
  error: null,

  setKaraokeQueue: (items) => set({ items }),

  addToKaraokeQueue: (item) =>
    set((state) => ({
      items: [...state.items, item],
    })),

  removeFromKaraokeQueue: (id) =>
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
    })),

  reorderKaraokeQueue: (items) => set({ items }),

  setCurrentSong: (currentSong) => set({ currentSong }),

  nextSong: () =>
    set((state) => {
      if (state.items.length === 0) {
        return { currentSong: null };
      }

      const nextItem = state.items[0];
      return {
        currentSong: nextItem,
        items: state.items.slice(1),
      };
    }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
