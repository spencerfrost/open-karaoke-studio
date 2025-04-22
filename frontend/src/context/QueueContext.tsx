import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { QueueItem, QueueItemWithSong } from '../types/Queue';
import { Song } from '../types/Song';

// State type
interface QueueState {
  items: QueueItemWithSong[];
  currentItem: QueueItemWithSong | null;
  isLoading: boolean;
  error: string | null;
}

// Action types
type QueueAction =
  | { type: 'SET_QUEUE'; payload: QueueItemWithSong[] }
  | { type: 'ADD_TO_QUEUE'; payload: QueueItemWithSong }
  | { type: 'REMOVE_FROM_QUEUE'; payload: string }
  | { type: 'REORDER_QUEUE'; payload: QueueItemWithSong[] }
  | { type: 'SET_CURRENT_ITEM'; payload: QueueItemWithSong | null }
  | { type: 'NEXT_ITEM' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

// Initial state
const initialState: QueueState = {
  items: [],
  currentItem: null,
  isLoading: false,
  error: null,
};

// Context
const QueueContext = createContext<{
  state: QueueState;
  dispatch: React.Dispatch<QueueAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer
const queueReducer = (state: QueueState, action: QueueAction): QueueState => {
  switch (action.type) {
    case 'SET_QUEUE':
      return {
        ...state,
        items: action.payload,
      };
    case 'ADD_TO_QUEUE':
      return {
        ...state,
        items: [...state.items, action.payload],
      };
    case 'REMOVE_FROM_QUEUE':
      return {
        ...state,
        items: state.items.filter((item) => item.id !== action.payload),
      };
    case 'REORDER_QUEUE':
      return {
        ...state,
        items: action.payload,
      };
    case 'SET_CURRENT_ITEM':
      return {
        ...state,
        currentItem: action.payload,
      };
    case 'NEXT_ITEM':
      if (state.items.length === 0) {
        return {
          ...state,
          currentItem: null,
        };
      }
      
      const nextItem = state.items[0];
      return {
        ...state,
        currentItem: nextItem,
        items: state.items.slice(1),
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

// Helper function to build QueueItemWithSong
export const buildQueueItemWithSong = (item: QueueItem, songs: Song[]): QueueItemWithSong | null => {
  const song = songs.find(s => s.id === item.songId);
  if (!song) return null;
  
  return {
    ...item,
    song
  };
};

// Provider component
export const QueueProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(queueReducer, initialState);

  return (
    <QueueContext.Provider value={{ state, dispatch }}>
      {children}
    </QueueContext.Provider>
  );
};

// Custom hook to use the queue context
export const useQueue = () => {
  const context = useContext(QueueContext);
  if (context === undefined) {
    throw new Error('useQueue must be used within a QueueProvider');
  }
  return context;
};
