import { create } from "zustand";
import { PlayerState, PlayerStatus, Lyric } from "../types/Player";
import { QueueItemWithSong } from "../types/Queue";

// Store state interface that extends PlayerState and adds actions
interface PlayerStore extends PlayerState {
  // Audio element references (managed separately outside the store)
  vocalsAudioRef?: HTMLAudioElement | null;
  instrumentalAudioRef?: HTMLAudioElement | null;

  // Actions
  setCurrentSong: (song: QueueItemWithSong | null) => void;
  setStatus: (status: PlayerStatus) => void;
  togglePlayPause: () => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;

  // Helper functions
  getCurrentLyric: () => { current: Lyric | null; next: Lyric | null };
  setAudioRefs: (
    vocals: HTMLAudioElement | null,
    instrumental: HTMLAudioElement | null,
  ) => void;
}

// Mock lyrics for development (you can keep this or integrate with real lyric data)
const mockLyrics: { [key: string]: Lyric[] } = {};

export const usePlayerStore = create<PlayerStore>((set, get) => ({
  // Initial state
  status: "idle",
  currentTime: 0,
  duration: 0,
  vocalVolume: 50,
  instrumentalVolume: 100,
  currentSong: null,
  seekTime: 0,

  // Actions
  setCurrentSong: (currentSong) =>
    set({
      currentSong,
      status: "idle",
      currentTime: 0,
    }),

  setStatus: (status) => set({ status }),

  togglePlayPause: () =>
    set((state) => ({
      status: state.status === "playing" ? "paused" : "playing",
    })),

  setCurrentTime: (currentTime) => set({ currentTime }),

  setDuration: (duration) => set({ duration }),

  setVocalVolume: (vocalVolume) => set({ vocalVolume }),

  setInstrumentalVolume: (instrumentalVolume) => set({ instrumentalVolume }),

  // Method to set audio refs
  setAudioRefs: (vocals, instrumental) =>
    set({
      vocalsAudioRef: vocals,
      instrumentalAudioRef: instrumental,
    }),

  // Helper function to get current lyric
  getCurrentLyric: () => {
    const state = get();

    if (!state.currentSong) {
      return { current: null, next: null };
    }

    const songId = state.currentSong.song.id;
    const lyrics = mockLyrics[songId] || [];
    const now = state.currentTime;

    // Find the current lyric (the last one with time <= currentTime)
    const currentLyrics = lyrics.filter((lyric) => lyric.time <= now);
    const current =
      currentLyrics.length > 0
        ? currentLyrics.reduce(
            (latest, lyric) => (lyric.time > latest.time ? lyric : latest),
            { time: 0, text: "" },
          )
        : null;

    // Find the next lyric (the first one with time > currentTime)
    const nextLyricIndex = lyrics.findIndex((lyric) => lyric.time > now);
    const next = nextLyricIndex !== -1 ? lyrics[nextLyricIndex] : null;

    return { current, next };
  },
}));
