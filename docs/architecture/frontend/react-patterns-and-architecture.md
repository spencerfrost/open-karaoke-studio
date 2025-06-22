# React Patterns Documentation - Open Karaoke Studio Frontend

**Investigation ID:** `frontend-017`  
**Status:** `documented`  
**Date:** 2025-06-15  
**Priority:** `high`

## 🎯 Overview

This investigation documents the comprehensive React patterns, architectural decisions, and implementation strategies used in the Open Karaoke Studio frontend. The frontend is built with modern React patterns, TypeScript integration, and a sophisticated state management approach combining Zustand, Context API, and TanStack Query.

## 🏗️ Architecture Overview

### Technology Stack

```typescript
// Core Technologies
- React 19+ (Functional Components with Hooks)
- TypeScript (Full type safety)
- Vite (Build tool and dev server)
- Tailwind CSS (Utility-first styling)
- Shadcn/UI (High-quality component library)

// State Management
- Zustand (Global state management)
- React Context (Configuration and settings)
- TanStack Query (Server state and caching)
- React Hooks (Local component state)

// Integration
- Socket.IO (Real-time WebSocket connections)
- REST APIs (Backend communication)
- File Upload (Media file handling)
```

## 🔧 State Management Patterns

### 1. Zustand Stores - Global Application State

**Pattern:** Centralized global state with persistent storage

```typescript
// Example: Settings Store with Persistence
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Initial state
      ...initialSettings,

      // Actions (mutations)
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
      name: "openKaraokeSettings", // localStorage key
    }
  )
);
```

**Key Stores:**

- `useSettingsStore` - App settings with localStorage persistence
- `useSongsStore` - Song library state and filtering
- `useKaraokePlayerStore` - WebSocket-based player state
- `useKaraokeQueueStore` - Queue management with real-time updates

**Benefits:**

- ✅ Type-safe state management
- ✅ Automatic persistence
- ✅ DevTools integration
- ✅ Minimal boilerplate

### 2. React Context - Configuration State

**Pattern:** Provider-based configuration for cross-cutting concerns

```typescript
// Settings Context with Reducer Pattern
const SettingsContext = createContext<{
  settings: AppSettings;
  dispatch: React.Dispatch<SettingsAction>;
}>({
  settings: initialSettings,
  dispatch: () => null,
});

// Reducer for complex state transitions
const settingsReducer = (
  state: AppSettings,
  action: SettingsAction
): AppSettings => {
  switch (action.type) {
    case "SET_THEME_SETTINGS":
      return {
        ...state,
        theme: { ...state.theme, ...action.payload },
      };
    // ... other cases
  }
};
```

**Usage:**

- Configuration state (themes, settings)
- Cross-component data sharing
- Complex state transitions with reducers

### 3. TanStack Query - Server State Management

**Pattern:** Declarative server state with caching and synchronization

```typescript
// Custom Hook with Query Abstraction
export function useSongs() {
  const queryClient = useQueryClient();

  // Queries
  const useSongs = (options = {}) => {
    return useApiQuery<Song[], typeof QUERY_KEYS.songs>(
      QUERY_KEYS.songs,
      "songs",
      options
    );
  };

  // Mutations with optimistic updates
  const useUpdateSong = () => {
    return useApiMutation<Song, { id: string; updates: Partial<Song> }>({
      mutationFn: ({ id, updates }) => apiSend(`songs/${id}`, "PATCH", updates),
      onSuccess: (updatedSong) => {
        // Update cache optimistically
        queryClient.setQueryData(QUERY_KEYS.song(updatedSong.id), updatedSong);
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
      },
    });
  };

  return { useSongs, useUpdateSong };
}
```

**Benefits:**

- ✅ Automatic background refetching
- ✅ Optimistic updates
- ✅ Cache management
- ✅ Loading/error states

## 🎨 Component Architecture Patterns

### 1. Compound Components with Shadcn/UI

**Pattern:** Composable UI components with consistent styling

```typescript
// Card Component Family
function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card text-card-foreground shadow-sm",
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    />
  );
}

// Export as compound component
export { Card, CardHeader, CardContent, CardFooter };
```

**Usage Pattern:**

```tsx
<Card>
  <CardHeader>
    <CardTitle>{song.title}</CardTitle>
    <CardDescription>{song.artist}</CardDescription>
  </CardHeader>
  <CardContent>{/* Song details */}</CardContent>
  <CardFooter>
    <Button onClick={handlePlay}>Play</Button>
  </CardFooter>
</Card>
```

### 2. Custom Hooks for Reusable Logic

**Pattern:** Encapsulated stateful logic with TypeScript

```typescript
// WebSocket Hook with Connection Management
export function useJobsWebSocket() {
  const [connected, setConnected] = useState(false);
  const [jobs, setJobs] = useState<JobData[]>([]);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    const socket = jobsWebSocketService.connect({
      onConnect: () => setConnected(true),
      onJobUpdate: (job) => {
        setJobs((prev) => prev.map((j) => (j.id === job.id ? job : j)));
        // Invalidate related queries
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      onDisconnect: () => setConnected(false),
    });

    return () => socket?.disconnect();
  }, [queryClient]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  return { connected, jobs, refetch: connect };
}
```

**Common Patterns:**

- API integration hooks (`useSongs`, `useMetadata`)
- WebSocket connection management
- Debounced values and search
- Infinite scrolling logic

### 3. TypeScript Integration Patterns

**Pattern:** Comprehensive type safety across components

```typescript
// Type-safe Component Props
interface SongCardProps {
  song: Song;
  onSelect: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onAddToQueue: (songId: string, singerName: string) => void;
  isSelected?: boolean;
  variant?: "default" | "compact";
}

// Type-safe API Response Handling
type ApiResponse<T> = {
  data: T | null;
  error: string | null;
};

// Generic Query Hook Types
function useApiQuery<TData, TQueryKey extends readonly unknown[]>(
  queryKey: TQueryKey,
  endpoint: string,
  options: UseQueryOptions<TData> = {}
) {
  return useQuery<TData>({
    queryKey,
    queryFn: () => apiGet<TData>(endpoint),
    ...options,
  });
}
```

### 4. Layout and Navigation Patterns

**Pattern:** Consistent layout structure with responsive design

```typescript
// App Layout with Navigation
const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen">
      {/* Background Effects */}
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative z-10">{children}</main>

      {/* Navigation */}
      <NavBar items={navigationItems} />
    </div>
  );
};

// Navigation Configuration
const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Stage", path: "/stage", icon: List },
  { name: "Controls", path: "/controls", icon: Sliders },
];
```

## 🔌 Integration Patterns

### 1. WebSocket Integration

**Pattern:** Real-time updates with automatic reconnection

```typescript
// WebSocket Service Class
class JobsWebSocketService {
  private socket: Socket | null = null;

  connect(callbacks: {
    onConnect?: () => void;
    onJobUpdate?: (job: JobData) => void;
    onDisconnect?: () => void;
  }) {
    this.socket = io(`${WEBSOCKET_URL}/jobs`);

    this.socket.on("connect", () => {
      console.log("Connected to job updates");
      callbacks.onConnect?.();
      this.socket?.emit("subscribe_to_jobs");
    });

    this.socket.on("job_update", callbacks.onJobUpdate);
    this.socket.on("disconnect", callbacks.onDisconnect);

    return this.socket;
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }
}
```

### 2. File Upload with Progress

**Pattern:** Type-safe file upload with progress tracking

```typescript
// Upload Hook with Progress
export function useUpload() {
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>(
    {}
  );

  const uploadFile = useCallback(
    async (
      file: File,
      endpoint: string,
      onProgress?: (progress: number) => void
    ) => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`/api/${endpoint}`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      return response.json();
    },
    []
  );

  return { uploadFile, uploadProgress };
}
```

### 3. Error Handling Patterns

**Pattern:** Consistent error boundaries and user feedback

```typescript
// Global Error Handling
function ApiErrorBoundary({ children }: { children: React.ReactNode }) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error("Unhandled API error:", event.reason);
      toast.error("An unexpected error occurred");
      setHasError(true);
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);
    return () => {
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection
      );
    };
  }, []);

  if (hasError) {
    return <ErrorFallback onReset={() => setHasError(false)} />;
  }

  return <>{children}</>;
}

// Hook-level error handling
const { data, error, isLoading } = useApiQuery(["songs"], "songs", {
  onError: (error) => {
    console.error("Failed to fetch songs:", error);
    toast.error("Failed to load songs");
  },
  retry: 3,
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
});
```

## 🎭 UI and Styling Patterns

### 1. Tailwind CSS Utility Classes

**Pattern:** Utility-first styling with design system consistency

```typescript
// Component with Tailwind Variants
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

// Usage with type safety
<Button variant="outline" size="sm" onClick={handleClick}>
  Action
</Button>;
```

### 2. Responsive Design Patterns

**Pattern:** Mobile-first responsive design

```typescript
// Responsive Grid Component
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {songs.map(song => (
    <SongCard key={song.id} song={song} />
  ))}
</div>

// Responsive Navigation
<nav className="flex lg:hidden fixed bottom-0 left-0 right-0 bg-background border-t">
  {navigationItems.map(item => (
    <NavLink
      key={item.path}
      to={item.path}
      className="flex-1 flex flex-col items-center py-2"
    >
      <item.icon size={20} />
      <span className="text-xs">{item.name}</span>
    </NavLink>
  ))}
</nav>
```

## 🚀 Performance Patterns

### 1. Infinite Scrolling

**Pattern:** Efficient large dataset rendering

```typescript
// Infinite Scroll Hook
export function useInfiniteScroll({
  hasMore,
  onLoadMore,
  threshold = 0.1,
  rootMargin = "100px",
}: UseInfiniteScrollOptions) {
  const [isFetching, setIsFetching] = useState(false);
  const targetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore && !isFetching) {
          setIsFetching(true);
          onLoadMore().finally(() => setIsFetching(false));
        }
      },
      { threshold, rootMargin }
    );

    const target = targetRef.current;
    if (target) observer.observe(target);

    return () => {
      if (target) observer.unobserve(target);
    };
  }, [hasMore, onLoadMore, threshold, rootMargin, isFetching]);

  return { targetRef, isFetching };
}
```

### 2. Debounced Search

**Pattern:** Efficient search with reduced API calls

```typescript
// Debounced Value Hook
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Usage in Search Component
const SearchableArtists: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearchTerm = useDebouncedValue(searchTerm, 300);

  const { data: artists } = useApiQuery(
    ["artists", debouncedSearchTerm],
    `artists?search=${debouncedSearchTerm}`,
    { enabled: debouncedSearchTerm.length > 0 }
  );

  return (
    <div>
      <Input
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="Search artists..."
      />
      {/* Render artists */}
    </div>
  );
};
```

## 📱 Mobile-First Patterns

### 1. Performance Controls for Mobile

**Pattern:** Dedicated mobile performance interface

```typescript
// Mobile Performance Controls Page
const PerformanceControlsPage: React.FC = () => {
  const {
    connect,
    disconnect,
    connected,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  } = useKaraokePlayerStore();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <AppLayout>
      <div className="flex flex-col gap-6 p-6">
        <WebSocketStatus connected={connected} />

        <PerformanceControlInput
          icon="volume-2"
          label="Vocal Volume"
          value={vocalVolume}
          onValueChange={([value]) => setVocalVolume(value)}
          min={0}
          max={100}
          valueDisplay={`${vocalVolume}%`}
        />

        <PerformanceControlInput
          icon="music"
          label="Instrumental Volume"
          value={instrumentalVolume}
          onValueChange={([value]) => setInstrumentalVolume(value)}
          min={0}
          max={100}
          valueDisplay={`${instrumentalVolume}%`}
        />
      </div>
    </AppLayout>
  );
};
```

### 2. Touch-Friendly Interface

**Pattern:** Mobile-optimized touch targets and gestures

```typescript
// Touch-Friendly Slider Component
<Slider
  value={[value]}
  min={min}
  max={max}
  step={step}
  onValueChange={onValueChange}
  variant="performance" // Larger touch targets
  className="w-full touch-manipulation"
  aria-label={label}
/>

// Mobile Queue Management
<div className="grid grid-cols-1 gap-2 p-4">
  {queueItems.map((item, index) => (
    <div
      key={item.id}
      className="flex items-center justify-between p-4 bg-card rounded-lg touch-manipulation"
    >
      <div className="flex-1 min-w-0">
        <h3 className="font-medium truncate">{item.song.title}</h3>
        <p className="text-sm text-muted-foreground truncate">{item.singerName}</p>
      </div>
      <Button
        variant="destructive"
        size="sm"
        onClick={() => removeFromQueue(item.id)}
        className="ml-4"
      >
        Remove
      </Button>
    </div>
  ))}
</div>
```

## 🔗 Cross-References

### Related Technical Investigations

- **Backend Integration:**

  - [016-backend-frontend-integration-disconnect](./016-backend-frontend-integration-disconnect.md) - API integration patterns
  - [../backend/004-service-layer-organization](../backend/004-service-layer-organization.md) - Service layer patterns

- **Architecture Decisions:**

  - [../architecture/state-management-evaluation.md](../architecture/state-management-evaluation.md) - State management choices
  - [../performance/frontend-optimization-strategies.md](../performance/frontend-optimization-strategies.md) - Performance patterns

- **API Documentation:**
  - [../../api/examples/javascript-examples.md](../../api/examples/javascript-examples.md) - API integration examples
  - [../../api/README.md](../../api/README.md) - API reference

### Implementation Examples

- **Live Code References:**
  - `/frontend/src/hooks/` - Custom hook implementations
  - `/frontend/src/stores/` - Zustand store patterns
  - `/frontend/src/components/ui/` - Shadcn component library
  - `/frontend/src/services/` - API service layer

## 📊 Key Benefits

### Development Experience

- ✅ **Type Safety** - Full TypeScript integration prevents runtime errors
- ✅ **Hot Reload** - Vite provides instant feedback during development
- ✅ **Component Library** - Shadcn/UI ensures consistent design
- ✅ **State DevTools** - Zustand and TanStack Query DevTools integration

### Performance

- ✅ **Bundle Optimization** - Vite tree-shaking and code splitting
- ✅ **Caching Strategy** - TanStack Query intelligent caching
- ✅ **Infinite Scrolling** - Efficient large dataset rendering
- ✅ **Debounced Search** - Reduced API calls

### User Experience

- ✅ **Real-time Updates** - WebSocket integration for live features
- ✅ **Mobile Optimization** - Touch-friendly responsive design
- ✅ **Error Handling** - Graceful error recovery and user feedback
- ✅ **Accessibility** - ARIA labels and keyboard navigation

### Maintainability

- ✅ **Modular Architecture** - Clear separation of concerns
- ✅ **Consistent Patterns** - Established coding conventions
- ✅ **Comprehensive Types** - Self-documenting code through TypeScript
- ✅ **Reusable Components** - DRY principle implementation

## 🎯 Implementation Guidelines

### 1. State Management Decision Tree

```
Does this state need to persist?
├─ Yes → Use Zustand with persist middleware
├─ No, but needs global access? → Use Zustand
├─ Server state? → Use TanStack Query
├─ Complex state transitions? → Use React Context with useReducer
└─ Simple local state? → Use useState
```

### 2. Component Creation Checklist

- [ ] Define TypeScript interfaces for props
- [ ] Implement responsive design with Tailwind
- [ ] Add proper ARIA labels for accessibility
- [ ] Include error boundaries where appropriate
- [ ] Implement loading states for async operations
- [ ] Add proper error handling and user feedback

### 3. Performance Optimization

- [ ] Use React.memo for expensive components
- [ ] Implement useCallback for stable function references
- [ ] Use useMemo for expensive calculations
- [ ] Implement infinite scrolling for large lists
- [ ] Debounce search inputs and API calls
- [ ] Optimize bundle size with dynamic imports

This comprehensive React patterns documentation serves as the definitive guide for understanding and implementing frontend patterns in the Open Karaoke Studio project, ensuring consistency, maintainability, and excellent user experience across all frontend development.
