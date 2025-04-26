import { create } from "zustand";
import { Song, SongStatus } from "../types/Song";

// Helper function for filtering songs based on criteria
const filterSongs = (
  songs: Song[],
  term: string,
  status: SongStatus | "all",
  favorites: boolean,
): Song[] => {
  return songs.filter((song) => {
    // Filter by search term
    const matchesTerm =
      !term ||
      song.title?.toLowerCase().includes(term.toLowerCase()) ||
      song.artist?.toLowerCase().includes(term.toLowerCase());

    // Filter by status
    const matchesStatus = status === "all" || song.status === status;

    // Filter by favorites
    const matchesFavorites = !favorites || song.favorite;

    return matchesTerm && matchesStatus && matchesFavorites;
  });
};

interface SongsState {
  // State
  songs: Song[];
  filteredSongs: Song[];
  filterTerm: string;
  filterStatus: SongStatus | "all";
  filterFavorites: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSongs: (songs: Song[]) => void;
  addSong: (song: Song) => void;
  updateSong: (id: string, updates: Partial<Song>) => void;
  removeSong: (id: string) => void;
  setFilterTerm: (term: string) => void;
  setFilterStatus: (status: SongStatus | "all") => void;
  setFilterFavorites: (favorites: boolean) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useSongsStore = create<SongsState>((set) => ({
  // Initial state
  songs: [],
  filteredSongs: [],
  filterTerm: "",
  filterStatus: "all",
  filterFavorites: false,
  isLoading: false,
  error: null,

  // Actions
  setSongs: (songs) =>
    set((state) => ({
      songs,
      filteredSongs: filterSongs(
        songs,
        state.filterTerm,
        state.filterStatus,
        state.filterFavorites,
      ),
    })),

  addSong: (song) =>
    set((state) => {
      const updatedSongs = [...state.songs, song];
      return {
        songs: updatedSongs,
        filteredSongs: filterSongs(
          updatedSongs,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites,
        ),
      };
    }),

  updateSong: (id, updates) =>
    set((state) => {
      const updatedSongs = state.songs.map((song) =>
        song.id === id ? { ...song, ...updates } : song,
      );

      return {
        songs: updatedSongs,
        filteredSongs: filterSongs(
          updatedSongs,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites,
        ),
      };
    }),

  removeSong: (id) =>
    set((state) => {
      const updatedSongs = state.songs.filter((song) => song.id !== id);

      return {
        songs: updatedSongs,
        filteredSongs: filterSongs(
          updatedSongs,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites,
        ),
      };
    }),

  setFilterTerm: (filterTerm) =>
    set((state) => ({
      filterTerm,
      filteredSongs: filterSongs(
        state.songs,
        filterTerm,
        state.filterStatus,
        state.filterFavorites,
      ),
    })),

  setFilterStatus: (filterStatus) =>
    set((state) => ({
      filterStatus,
      filteredSongs: filterSongs(
        state.songs,
        state.filterTerm,
        filterStatus,
        state.filterFavorites,
      ),
    })),

  setFilterFavorites: (filterFavorites) =>
    set((state) => ({
      filterFavorites,
      filteredSongs: filterSongs(
        state.songs,
        state.filterTerm,
        state.filterStatus,
        filterFavorites,
      ),
    })),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
