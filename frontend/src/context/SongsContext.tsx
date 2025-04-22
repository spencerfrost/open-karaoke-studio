import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { Song, SongStatus } from '../types/Song';

// State type
interface SongsState {
  songs: Song[];
  filteredSongs: Song[];
  filterTerm: string;
  filterStatus: SongStatus | 'all';
  filterFavorites: boolean;
  isLoading: boolean;
  error: string | null;
}

// Action types
type SongsAction =
  | { type: 'SET_SONGS'; payload: Song[] }
  | { type: 'ADD_SONG'; payload: Song }
  | { type: 'UPDATE_SONG'; payload: { id: string; updates: Partial<Song> } }
  | { type: 'REMOVE_SONG'; payload: string }
  | { type: 'SET_FILTER_TERM'; payload: string }
  | { type: 'SET_FILTER_STATUS'; payload: SongStatus | 'all' }
  | { type: 'SET_FILTER_FAVORITES'; payload: boolean }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

// Initial state
const initialState: SongsState = {
  songs: [],
  filteredSongs: [],
  filterTerm: '',
  filterStatus: 'all',
  filterFavorites: false,
  isLoading: false,
  error: null,
};

// Context
const SongsContext = createContext<{
  state: SongsState;
  dispatch: React.Dispatch<SongsAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer
const songsReducer = (state: SongsState, action: SongsAction): SongsState => {
  switch (action.type) {
    case 'SET_SONGS':
      return {
        ...state,
        songs: action.payload,
        filteredSongs: filterSongs(
          action.payload,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites
        ),
      };
    case 'ADD_SONG':
      const updatedSongs = [...state.songs, action.payload];
      return {
        ...state,
        songs: updatedSongs,
        filteredSongs: filterSongs(
          updatedSongs,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites
        ),
      };
    case 'UPDATE_SONG':
      const updatedSongsList = state.songs.map((song) =>
        song.id === action.payload.id
          ? { ...song, ...action.payload.updates }
          : song
      );
      return {
        ...state,
        songs: updatedSongsList,
        filteredSongs: filterSongs(
          updatedSongsList,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites
        ),
      };
    case 'REMOVE_SONG':
      const songsAfterRemoval = state.songs.filter(
        (song) => song.id !== action.payload
      );
      return {
        ...state,
        songs: songsAfterRemoval,
        filteredSongs: filterSongs(
          songsAfterRemoval,
          state.filterTerm,
          state.filterStatus,
          state.filterFavorites
        ),
      };
    case 'SET_FILTER_TERM':
      return {
        ...state,
        filterTerm: action.payload,
        filteredSongs: filterSongs(
          state.songs,
          action.payload,
          state.filterStatus,
          state.filterFavorites
        ),
      };
    case 'SET_FILTER_STATUS':
      return {
        ...state,
        filterStatus: action.payload,
        filteredSongs: filterSongs(
          state.songs,
          state.filterTerm,
          action.payload,
          state.filterFavorites
        ),
      };
    case 'SET_FILTER_FAVORITES':
      return {
        ...state,
        filterFavorites: action.payload,
        filteredSongs: filterSongs(
          state.songs,
          state.filterTerm,
          state.filterStatus,
          action.payload
        ),
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    default:
      return state;
  }
};

// Filter function
const filterSongs = (
  songs: Song[],
  term: string,
  status: SongStatus | 'all',
  favorites: boolean
): Song[] => {
  return songs.filter((song) => {
    // Filter by search term
    const matchesTerm =
      term === '' ||
      song.title.toLowerCase().includes(term.toLowerCase()) ||
      song.artist.toLowerCase().includes(term.toLowerCase());

    // Filter by status
    const matchesStatus = status === 'all' || song.status === status;

    // Filter by favorites
    const matchesFavorites = !favorites || song.favorite;

    return matchesTerm && matchesStatus && matchesFavorites;
  });
};

// Provider component
export const SongsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(songsReducer, initialState);

  return (
    <SongsContext.Provider value={{ state, dispatch }}>
      {children}
    </SongsContext.Provider>
  );
};

// Custom hook to use the songs context
export const useSongs = () => {
  const context = useContext(SongsContext);
  if (context === undefined) {
    throw new Error('useSongs must be used within a SongsProvider');
  }
  return context;
};
