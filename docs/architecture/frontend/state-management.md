# State Management - Open Karaoke Studio Frontend

**Last Updated**: June 15, 2025  
**Status**: Current Implementation  
**Technologies**: Zustand • React Context • TanStack Query • React Hooks

## 🎯 Overview

The Open Karaoke Studio frontend uses a layered state management approach that combines different tools for different types of state. This architecture provides type safety, persistence, and excellent developer experience while maintaining clear separation of concerns.

## 🏗️ State Management Layers

### 1. Global Application State (Zustand)
For application-wide state that needs persistence and cross-component access.

### 2. Server State (TanStack Query)  
For data fetched from the backend API with caching and synchronization.

### 3. Configuration State (React Context)
For application configuration and settings that rarely change.

### 4. Local Component State (React Hooks)
For UI-specific state that doesn't need to be shared.

## 🏪 Global State (Zustand Stores)

### Settings Store
Persistent application settings with localStorage integration:

```typescript
interface SettingsState {
  theme: {
    mode: 'light' | 'dark' | 'system';
    accentColor: string;
  };
  audio: {
    volume: number;
    effects: boolean;
  };
  preferences: {
    autoplay: boolean;
    notifications: boolean;
  };
  // Actions
  setThemeSettings: (settings: Partial<SettingsState['theme']>) => void;
  setAudioSettings: (settings: Partial<SettingsState['audio']>) => void;
  resetSettings: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: {
        mode: 'system',
        accentColor: '#3b82f6',
      },
      audio: {
        volume: 0.8,
        effects: true,
      },
      preferences: {
        autoplay: false,
        notifications: true,
      },
      
      setThemeSettings: (themeSettings) =>
        set((state) => ({
          theme: { ...state.theme, ...themeSettings },
        })),
        
      setAudioSettings: (audioSettings) =>
        set((state) => ({
          audio: { ...state.audio, ...audioSettings },
        })),
        
      resetSettings: () => set(initialSettings),
    }),
    {
      name: "openKaraokeSettings",
      version: 1,
    },
  ),
);
```

### Songs Store
Song library state with filtering and search:

```typescript
interface SongsState {
  // State
  filters: {
    search: string;
    genre: string | null;
    artist: string | null;
    source: 'all' | 'itunes' | 'youtube';
  };
  sortBy: 'title' | 'artist' | 'dateAdded' | 'playCount';
  sortOrder: 'asc' | 'desc';
  selectedSong: Song | null;
  
  // Actions
  setFilters: (filters: Partial<SongsState['filters']>) => void;
  setSorting: (sortBy: SongsState['sortBy'], order: SongsState['sortOrder']) => void;
  setSelectedSong: (song: Song | null) => void;
  clearFilters: () => void;
}

export const useSongsStore = create<SongsState>((set) => ({
  filters: {
    search: '',
    genre: null,
    artist: null,
    source: 'all',
  },
  sortBy: 'title',
  sortOrder: 'asc',
  selectedSong: null,
  
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    })),
    
  setSorting: (sortBy, sortOrder) =>
    set({ sortBy, sortOrder }),
    
  setSelectedSong: (selectedSong) =>
    set({ selectedSong }),
    
  clearFilters: () =>
    set({
      filters: {
        search: '',
        genre: null,
        artist: null,
        source: 'all',
      },
    }),
}));
```

### Karaoke Player Store
Real-time player state synchronized with WebSocket:

```typescript
interface KaraokePlayerState {
  // Current state
  isPlaying: boolean;
  currentSong: Song | null;
  position: number;
  duration: number;
  volume: number;
  
  // WebSocket connection
  connected: boolean;
  reconnecting: boolean;
  
  // Actions
  play: () => void;
  pause: () => void;
  seek: (position: number) => void;
  setVolume: (volume: number) => void;
  loadSong: (song: Song) => void;
}

export const useKaraokePlayerStore = create<KaraokePlayerState>((set, get) => ({
  isPlaying: false,
  currentSong: null,
  position: 0,
  duration: 0,
  volume: 0.8,
  connected: false,
  reconnecting: false,
  
  play: () => {
    // Emit WebSocket event and update local state
    playerWebSocket.emit('play');
    set({ isPlaying: true });
  },
  
  pause: () => {
    playerWebSocket.emit('pause');
    set({ isPlaying: false });
  },
  
  seek: (position) => {
    playerWebSocket.emit('seek', { position });
    set({ position });
  },
  
  setVolume: (volume) => {
    playerWebSocket.emit('volume', { volume });
    set({ volume });
  },
  
  loadSong: (song) => {
    playerWebSocket.emit('load_song', { songId: song.id });
    set({ currentSong: song, position: 0, isPlaying: false });
  },
}));
```

### Queue Management Store
Real-time queue state with WebSocket updates:

```typescript
interface QueueState {
  // Queue data
  currentQueue: QueueEntry[];
  currentEntry: QueueEntry | null;
  nextEntry: QueueEntry | null;
  
  // Queue management
  addToQueue: (songId: string, singerName: string) => void;
  removeFromQueue: (entryId: string) => void;
  reorderQueue: (entries: QueueEntry[]) => void;
  playNext: () => void;
  skipCurrent: () => void;
}

export const useKaraokeQueueStore = create<QueueState>((set, get) => ({
  currentQueue: [],
  currentEntry: null,
  nextEntry: null,
  
  addToQueue: (songId, singerName) => {
    const entry: Omit<QueueEntry, 'id'> = {
      songId,
      singerName,
      addedAt: new Date().toISOString(),
      status: 'waiting',
    };
    
    // Emit to WebSocket and update optimistically
    queueWebSocket.emit('add_to_queue', entry);
    
    set((state) => ({
      currentQueue: [...state.currentQueue, { ...entry, id: Date.now().toString() }],
    }));
  },
  
  removeFromQueue: (entryId) => {
    queueWebSocket.emit('remove_from_queue', { entryId });
    
    set((state) => ({
      currentQueue: state.currentQueue.filter(entry => entry.id !== entryId),
    }));
  },
  
  reorderQueue: (entries) => {
    queueWebSocket.emit('reorder_queue', { entries });
    set({ currentQueue: entries });
  },
}));
```

## 🌐 Server State (TanStack Query)

### Query Configuration
Central configuration for API queries:

```typescript
// Query client setup
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Query keys for cache management
export const QUERY_KEYS = {
  songs: ['songs'] as const,
  song: (id: string) => ['songs', id] as const,
  artists: ['artists'] as const,
  genres: ['genres'] as const,
  queue: ['queue'] as const,
  jobs: ['jobs'] as const,
} as const;
```

### Songs API Integration
Comprehensive song data management:

```typescript
export function useSongs() {
  const queryClient = useQueryClient();
  
  // Queries
  const useAllSongs = (options: UseQueryOptions<Song[]> = {}) => {
    return useQuery({
      queryKey: QUERY_KEYS.songs,
      queryFn: () => apiGet<Song[]>('songs'),
      ...options,
    });
  };
  
  const useSong = (id: string) => {
    return useQuery({
      queryKey: QUERY_KEYS.song(id),
      queryFn: () => apiGet<Song>(`songs/${id}`),
      enabled: !!id,
    });
  };
  
  // Mutations
  const useUpdateSong = () => {
    return useMutation({
      mutationFn: ({ id, updates }: { id: string; updates: Partial<Song> }) =>
        apiSend(`songs/${id}`, 'PATCH', updates),
      onSuccess: (updatedSong) => {
        // Update individual song cache
        queryClient.setQueryData(QUERY_KEYS.song(updatedSong.id), updatedSong);
        
        // Update songs list cache optimistically
        queryClient.setQueryData<Song[]>(QUERY_KEYS.songs, (oldSongs) =>
          oldSongs?.map(song => 
            song.id === updatedSong.id ? updatedSong : song
          ) ?? []
        );
      },
      onError: () => {
        // Invalidate queries on error to refetch fresh data
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
      },
    });
  };
  
  const useDeleteSong = () => {
    return useMutation({
      mutationFn: (id: string) => apiSend(`songs/${id}`, 'DELETE'),
      onSuccess: (_, deletedId) => {
        // Remove from cache
        queryClient.removeQueries({ queryKey: QUERY_KEYS.song(deletedId) });
        
        // Update songs list
        queryClient.setQueryData<Song[]>(QUERY_KEYS.songs, (oldSongs) =>
          oldSongs?.filter(song => song.id !== deletedId) ?? []
        );
      },
    });
  };
  
  return {
    useAllSongs,
    useSong,
    useUpdateSong,
    useDeleteSong,
  };
}
```

### Upload Progress Tracking
Real-time upload status with TanStack Query:

```typescript
export function useUploadJobs() {
  return useQuery({
    queryKey: QUERY_KEYS.jobs,
    queryFn: () => apiGet<JobData[]>('jobs'),
    refetchInterval: 2000, // Poll every 2 seconds for active jobs
    refetchIntervalInBackground: false,
  });
}

export function useUploadSong() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiUpload('songs/upload', formData);
    },
    onSuccess: () => {
      // Invalidate songs and jobs queries to fetch updated data
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.jobs });
    },
  });
}
```

## ⚙️ Configuration State (React Context)

### App Configuration Context
For application-wide settings that rarely change:

```typescript
interface AppConfigContextType {
  apiBaseUrl: string;
  wsBaseUrl: string;
  features: {
    uploadEnabled: boolean;
    queueEnabled: boolean;
    editingEnabled: boolean;
  };
  limits: {
    maxUploadSize: number;
    maxQueueSize: number;
  };
}

const AppConfigContext = createContext<AppConfigContextType | null>(null);

export function AppConfigProvider({ children }: { children: React.ReactNode }) {
  const config: AppConfigContextType = {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000',
    wsBaseUrl: import.meta.env.VITE_WS_BASE_URL ?? 'http://localhost:5000',
    features: {
      uploadEnabled: import.meta.env.VITE_UPLOAD_ENABLED === 'true',
      queueEnabled: import.meta.env.VITE_QUEUE_ENABLED === 'true',
      editingEnabled: import.meta.env.VITE_EDITING_ENABLED === 'true',
    },
    limits: {
      maxUploadSize: 100 * 1024 * 1024, // 100MB
      maxQueueSize: 50,
    },
  };
  
  return (
    <AppConfigContext.Provider value={config}>
      {children}
    </AppConfigContext.Provider>
  );
}

export function useAppConfig() {
  const context = useContext(AppConfigContext);
  if (!context) {
    throw new Error('useAppConfig must be used within AppConfigProvider');
  }
  return context;
}
```

## 🎣 Local Component State (React Hooks)

### Custom Hooks for Reusable Logic

#### WebSocket Connection Hook
```typescript
export function useWebSocketConnection(url: string, options: {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
} = {}) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const socketRef = useRef<Socket | null>(null);
  
  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;
    
    socketRef.current = io(url);
    
    socketRef.current.on('connect', () => {
      setConnected(true);
      setError(null);
      options.onConnect?.();
    });
    
    socketRef.current.on('disconnect', () => {
      setConnected(false);
      options.onDisconnect?.();
    });
    
    socketRef.current.on('connect_error', (err) => {
      setError(err);
      options.onError?.(err);
    });
  }, [url, options]);
  
  const disconnect = useCallback(() => {
    socketRef.current?.disconnect();
    socketRef.current = null;
    setConnected(false);
  }, []);
  
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);
  
  return {
    socket: socketRef.current,
    connected,
    error,
    connect,
    disconnect,
  };
}
```

#### Debounced Search Hook
```typescript
export function useDebouncedSearch(initialValue = '', delay = 300) {
  const [searchTerm, setSearchTerm] = useState(initialValue);
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(initialValue);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, delay);
    
    return () => {
      clearTimeout(handler);
    };
  }, [searchTerm, delay]);
  
  return {
    searchTerm,
    debouncedSearchTerm,
    setSearchTerm,
  };
}
```

#### Form State Hook
```typescript
export function useFormState<T>(initialState: T, validate?: (data: T) => Record<string, string>) {
  const [data, setData] = useState<T>(initialState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  
  const setValue = useCallback((field: keyof T, value: T[keyof T]) => {
    setData(prev => ({ ...prev, [field]: value }));
    setTouched(prev => ({ ...prev, [field]: true }));
    
    if (validate) {
      const newErrors = validate({ ...data, [field]: value });
      setErrors(newErrors);
    }
  }, [data, validate]);
  
  const reset = useCallback(() => {
    setData(initialState);
    setErrors({});
    setTouched({});
  }, [initialState]);
  
  const isValid = Object.keys(errors).length === 0;
  
  return {
    data,
    errors,
    touched,
    isValid,
    setValue,
    reset,
  };
}
```

## 🔄 State Synchronization Patterns

### WebSocket State Sync
Synchronizing Zustand stores with WebSocket events:

```typescript
// Queue store WebSocket integration
export function useQueueWebSocketSync() {
  const { setCurrentQueue, setCurrentEntry } = useKaraokeQueueStore();
  
  useWebSocketConnection(`${WS_BASE_URL}/queue`, {
    onConnect: () => {
      console.log('Connected to queue updates');
    },
  });
  
  useEffect(() => {
    if (!socket) return;
    
    socket.on('queue_updated', (queue: QueueEntry[]) => {
      setCurrentQueue(queue);
    });
    
    socket.on('current_entry_changed', (entry: QueueEntry | null) => {
      setCurrentEntry(entry);
    });
    
    return () => {
      socket.off('queue_updated');
      socket.off('current_entry_changed');
    };
  }, [socket, setCurrentQueue, setCurrentEntry]);
}
```

### Optimistic Updates
Updating UI immediately while syncing with server:

```typescript
export function useOptimisticSongUpdate() {
  const queryClient = useQueryClient();
  const { mutate: updateSong } = useUpdateSong();
  
  const updateSongOptimistic = useCallback((id: string, updates: Partial<Song>) => {
    // Update UI immediately
    queryClient.setQueryData<Song>(QUERY_KEYS.song(id), (oldSong) =>
      oldSong ? { ...oldSong, ...updates } : undefined
    );
    
    // Send to server
    updateSong({ id, updates }, {
      onError: () => {
        // Revert on error
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(id) });
      },
    });
  }, [queryClient, updateSong]);
  
  return { updateSongOptimistic };
}
```

## 🧪 Testing State Management

### Store Testing
```typescript
// Testing Zustand stores
describe('useSongsStore', () => {
  beforeEach(() => {
    useSongsStore.getState().clearFilters();
  });
  
  it('updates filters correctly', () => {
    const { setFilters } = useSongsStore.getState();
    
    setFilters({ search: 'test', genre: 'rock' });
    
    const state = useSongsStore.getState();
    expect(state.filters.search).toBe('test');
    expect(state.filters.genre).toBe('rock');
  });
});
```

### Hook Testing
```typescript
// Testing custom hooks
describe('useDebouncedSearch', () => {
  it('debounces search term correctly', async () => {
    const { result } = renderHook(() => useDebouncedSearch('', 100));
    
    act(() => {
      result.current.setSearchTerm('test');
    });
    
    expect(result.current.searchTerm).toBe('test');
    expect(result.current.debouncedSearchTerm).toBe('');
    
    await waitFor(() => {
      expect(result.current.debouncedSearchTerm).toBe('test');
    });
  });
});
```

## 📊 State Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│ Component State  │───▶│  Local Actions  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Global Actions  │◀───│  Zustand Store   │───▶│ WebSocket Emit  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  API Mutation   │───▶│ TanStack Query   │◀───│ WebSocket Event │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Backend API     │───▶│  Cache Update    │───▶│ UI Re-render    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

**Next Steps**: Explore the [UI Design System](ui-design-system.md) to understand how these state management patterns integrate with the component architecture and styling system.
