import { create } from "zustand";
import { MiniPlayerPosition } from "./shared/types";

export interface UIPreferencesState {
  // Lyrics settings
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number;
  autoScrollEnabled: boolean;
  showChords: boolean;

  // Song metadata for display
  songTitle: string | null;
  songArtist: string | null;

  // Mini-player state
  miniPlayerEnabled: boolean;
  miniPlayerPosition: MiniPlayerPosition;
  miniPlayerDismissed: boolean; // User explicitly closed it for current song

  // Actions
  setLyricsSize: (size: "small" | "medium" | "large") => void;
  setLyricsOffset: (offset: number) => void;
  setAutoScrollEnabled: (enabled: boolean) => void;
  setShowChords: (enabled: boolean) => void;
  setSongMetadata: (title: string | null, artist: string | null) => void;
  setMiniPlayerEnabled: (enabled: boolean) => void;
  setMiniPlayerPosition: (position: MiniPlayerPosition) => void;
  dismissMiniPlayer: () => void;
  resetMiniPlayerDismissed: () => void;
}

export const useUIPreferencesStore = create<UIPreferencesState>((set) => ({
  // Default values
  lyricsSize: "medium",
  lyricsOffset: 0,
  autoScrollEnabled: true,
  showChords: false,
  songTitle: null,
  songArtist: null,
  miniPlayerEnabled: true,
  miniPlayerPosition: { x: 24, y: 24 }, // Bottom-right with 24px margin
  miniPlayerDismissed: false,

  setLyricsSize: (size: "small" | "medium" | "large") => {
    set({ lyricsSize: size });
  },

  setLyricsOffset: (offset: number) => {
    set({ lyricsOffset: offset });
  },

  setAutoScrollEnabled: (enabled: boolean) => {
    set({ autoScrollEnabled: enabled });
  },

  setShowChords: (enabled: boolean) => {
    set({ showChords: enabled });
  },

  setSongMetadata: (title: string | null, artist: string | null) => {
    set({ songTitle: title, songArtist: artist });
  },

  setMiniPlayerEnabled: (enabled: boolean) => {
    set({ miniPlayerEnabled: enabled });
  },

  setMiniPlayerPosition: (position: MiniPlayerPosition) => {
    set({ miniPlayerPosition: position });
  },

  dismissMiniPlayer: () => {
    set({ miniPlayerDismissed: true });
  },

  resetMiniPlayerDismissed: () => {
    set({ miniPlayerDismissed: false });
  },
}));
