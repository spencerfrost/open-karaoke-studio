# Component Architecture - Open Karaoke Studio Frontend

**Last Updated**: June 15, 2025
**Status**: Current Implementation
**Framework**: React 19+ with TypeScript

## 🎯 Overview

The Open Karaoke Studio frontend uses a layered component architecture built on modern React patterns, TypeScript, and the Shadcn/UI design system. The architecture emphasizes reusability, type safety, and excellent developer experience while maintaining consistent visual design.

## 🏗️ Architecture Layers

### Dual Display Library Architecture _(New)_

The library page implements a sophisticated dual-display system combining search and browsing:

```typescript
// Main Library Container
function LibraryContent() {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedQuery = useDebounce(searchQuery, 300);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Song Results Section - Prominent search results */}
      <SongResultsSection query={debouncedQuery} className="lg:order-1" />

      {/* Artist Browsing Section - Alphabetical browsing */}
      <ArtistResultsSection className="lg:order-2" />
    </div>
  );
}

// Infinite Scroll Song Search
function SongResultsSection({ query }: { query: string }) {
  const { data, fetchNextPage, hasNextPage, isLoading } =
    useInfiniteFuzzySearch(query);

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Songs</h2>
      <SongResultsGrid
        data={data}
        onLoadMore={fetchNextPage}
        hasMore={hasNextPage}
        loading={isLoading}
      />
    </section>
  );
}

// Expandable Artist Accordion
function ArtistResultsSection() {
  const { data: artists, fetchNextPage, hasNextPage } = useInfiniteArtists();

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Artists</h2>
      <InfiniteArtistAccordion
        artists={artists}
        onLoadMore={fetchNextPage}
        hasMore={hasNextPage}
      />
    </section>
  );
}
```

**Key Features**:

- **Dual Infinite Queries** - Separate pagination for songs and artists
- **Conditional Loading** - Artist songs load only when expanded
- **Debounced Search** - 300ms delay to optimize API calls
- **Performance Optimized** - React Query caching and intersection observers

### 1. Base Components (Shadcn/UI)

Foundation layer providing accessible, unstyled primitives:

```typescript
// Base UI primitives with consistent styling
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
```

**Characteristics**:

- Accessible by default (ARIA support)
- Consistent styling with CSS variables
- Polymorphic component patterns
- Full TypeScript support

### 2. Composite Components

Domain-specific combinations of base components:

```typescript
// Example: Song Card Component
function SongCard({ song, onPlay, onDetails }: SongCardProps) {
  return (
    <Card className="group cursor-pointer hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <ArtworkDisplay song={song} size="sm" className="rounded-md" />
          <div className="flex-1 min-w-0">
            <CardTitle className="line-clamp-1">{song.title}</CardTitle>
            <CardDescription className="line-clamp-1">
              {song.artist}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center justify-between">
          <SourceBadges song={song} />
          <Button size="sm" onClick={() => onPlay(song)}>
            Play
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 3. Feature Components

Complete user workflows and complex interactions:

```typescript
// Example: Song Details Dialog
function SongDetailsDialog({ song, open, onClose }: SongDetailsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>{song.title}</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ArtworkDisplay song={song} size="lg" />
          <PrimarySongDetails song={song} />
        </div>

        <SongLyricsSection lyrics={song.lyrics} />

        {song.itunesPreviewUrl && (
          <SongPreviewPlayer
            previewUrl={song.itunesPreviewUrl}
            title={song.title}
            artist={song.artist}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
```

### 4. Page Components

Route-level containers that orchestrate features:

```typescript
// Example: Library Page
function LibraryPage() {
  const { data: songs, isLoading } = useSongs();
  const [selectedSong, setSelectedSong] = useState<Song | null>(null);

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <SearchInterface onSearch={handleSearch} />
        <LibraryFilters onFilter={handleFilter} />
      </div>

      <SongGrid
        songs={songs}
        loading={isLoading}
        onSongSelect={setSelectedSong}
      />

      <SongDetailsDialog
        song={selectedSong}
        open={!!selectedSong}
        onClose={() => setSelectedSong(null)}
      />
    </div>
  );
}
```

## 🎨 Design System Integration

### Shadcn/UI Foundation

The design system is built on Shadcn/UI components with Tailwind CSS:

```typescript
// Consistent styling through CSS variables
const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
));
```

**Key Features**:

- **CSS Variables** for theme consistency
- **Utility Classes** for responsive design
- **Component Variants** using class-variance-authority
- **Dark Mode Support** through CSS variable switching

### Theme System

```typescript
// tailwind.config.js theme extension
module.exports = {
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... additional color variables
      },
    },
  },
};
```

## 🔧 Component Patterns

### 1. Compound Components

For flexible, composable interfaces:

```typescript
// Flexible card composition
<Card>
  <CardHeader>
    <CardTitle>Song Title</CardTitle>
    <CardDescription>Artist Name</CardDescription>
  </CardHeader>
  <CardContent>
    <SongDetails song={song} />
  </CardContent>
  <CardFooter>
    <ActionButtons song={song} />
  </CardFooter>
</Card>
```

### 2. Render Props / Children Functions

For flexible data presentation:

```typescript
interface SongGridProps {
  songs: Song[];
  children: (song: Song, index: number) => React.ReactNode;
}

function SongGrid({ songs, children }: SongGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {songs.map((song, index) => (
        <div key={song.id}>{children(song, index)}</div>
      ))}
    </div>
  );
}

// Usage with flexibility
<SongGrid songs={songs}>
  {(song) => (
    <SongCard
      song={song}
      onSelect={() => handleSelect(song)}
      variant="compact"
    />
  )}
</SongGrid>;
```

### 3. Custom Hooks for Logic Abstraction

Reusable logic patterns:

```typescript
// Song interaction hook
function useSongActions() {
  const { mutate: updateSong } = useUpdateSong();
  const { mutate: deleteSong } = useDeleteSong();

  const handlePlay = useCallback(
    (song: Song) => {
      // Navigate to player or add to queue
      router.push(`/karaoke/${song.id}`);
    },
    [router]
  );

  const handleEdit = useCallback(
    (song: Song, updates: Partial<Song>) => {
      updateSong({ id: song.id, updates });
    },
    [updateSong]
  );

  const handleDelete = useCallback(
    (songId: string) => {
      deleteSong(songId);
    },
    [deleteSong]
  );

  return { handlePlay, handleEdit, handleDelete };
}
```

### 4. Error Boundaries

Graceful error handling:

```typescript
class SongGridErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 text-center">
          <h2 className="text-lg font-semibold mb-2">
            Something went wrong loading songs
          </h2>
          <Button onClick={() => this.setState({ hasError: false })}>
            Try Again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## 📱 Responsive Design Patterns

### Mobile-First Approach

Components are designed for mobile first, then enhanced for larger screens:

```typescript
function SongCard({ song }: SongCardProps) {
  return (
    <Card className="w-full">
      {/* Mobile layout (default) */}
      <div className="p-4">
        <div className="flex items-center gap-3">
          <ArtworkDisplay song={song} size="sm" />
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{song.title}</h3>
            <p className="text-sm text-muted-foreground truncate">
              {song.artist}
            </p>
          </div>
        </div>

        {/* Desktop enhancements */}
        <div className="hidden md:block mt-4">
          <SongMetadata song={song} />
        </div>
      </div>
    </Card>
  );
}
```

### Breakpoint Strategy

```typescript
// Tailwind breakpoints used consistently
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px' // Extra large
};

// Component responsive patterns
<div className="
  grid
  grid-cols-1
  sm:grid-cols-2
  lg:grid-cols-3
  xl:grid-cols-4
  gap-4
">
```

## 🔄 State Integration Patterns

### Local Component State

For UI-specific state that doesn't need to be shared:

```typescript
function SongPreviewPlayer({ previewUrl }: SongPreviewPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  const handlePlayPause = useCallback(() => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  return (
    <div className="flex items-center gap-2">
      <Button size="sm" onClick={handlePlayPause}>
        {isPlaying ? <Pause /> : <Play />}
      </Button>
      <div className="flex-1">
        <ProgressBar value={currentTime} max={30} />
      </div>
      <audio ref={audioRef} src={previewUrl} />
    </div>
  );
}
```

### Global State Integration

Components that need to interact with global state:

```typescript
function LibraryFilters() {
  const { filters, setFilters } = useSongsStore();

  return (
    <div className="flex gap-2 flex-wrap">
      <Select
        value={filters.genre}
        onValueChange={(genre) => setFilters({ ...filters, genre })}
      >
        <SelectTrigger>
          <SelectValue placeholder="Genre" />
        </SelectTrigger>
        <SelectContent>
          {genres.map((genre) => (
            <SelectItem key={genre} value={genre}>
              {genre}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

## 🧪 Testing Patterns

### Component Testing

```typescript
// Component test example
describe("SongCard", () => {
  it("displays song information correctly", () => {
    const mockSong = {
      id: "1",
      title: "Test Song",
      artist: "Test Artist",
      album: "Test Album",
    };

    render(<SongCard song={mockSong} onSelect={jest.fn()} />);

    expect(screen.getByText("Test Song")).toBeInTheDocument();
    expect(screen.getByText("Test Artist")).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const mockOnSelect = jest.fn();
    const mockSong = createMockSong();

    render(<SongCard song={mockSong} onSelect={mockOnSelect} />);

    fireEvent.click(screen.getByTestId("song-card"));
    expect(mockOnSelect).toHaveBeenCalledWith(mockSong);
  });
});
```

## 📁 File Organization

### Component Directory Structure

```
components/
├── ui/                   # Shadcn base components
│   ├── button.tsx
│   ├── card.tsx
│   └── dialog.tsx
├── library/             # Dual display library components (New)
│   ├── LibraryContent.tsx          # Main dual-display orchestrator
│   ├── LibrarySearchInput.tsx      # Unified search input
│   ├── SongResultsSection.tsx      # Song search results container
│   ├── ArtistResultsSection.tsx    # Artist browsing container
│   ├── SongResultsGrid.tsx         # Infinite scroll song grid
│   ├── ArtistAccordion.tsx         # Base artist accordion
│   ├── InfiniteArtistAccordion.tsx # Infinite scroll artist list
│   └── ArtistSection.tsx           # Individual artist sections
├── songs/               # Song-related components
│   ├── SongCard.tsx              # Grid-based song display
│   ├── HorizontalSongCard.tsx    # Compact horizontal song cards
│   ├── SongGrid.tsx
│   ├── SongDetailsDialog.tsx
│   └── SongPreviewPlayer.tsx
├── layout/              # Layout components
│   ├── Navigation.tsx
│   ├── Header.tsx
│   └── Footer.tsx
├── forms/               # Form components
│   ├── SearchForm.tsx
│   └── UploadForm.tsx
└── common/              # Shared utility components
    ├── LoadingSpinner.tsx
    ├── ErrorBoundary.tsx
    └── ProgressBar.tsx
```

### Component Naming Conventions

- **PascalCase** for component files and names
- **camelCase** for props and handlers
- **kebab-case** for CSS classes and data attributes
- **UPPER_SNAKE_CASE** for constants

## 🔗 Integration Points

### Backend API Integration

Components integrate with the backend through:

- **TanStack Query** for data fetching
- **Custom hooks** for API abstraction
- **Error boundaries** for graceful failure handling

### WebSocket Integration

Real-time features through:

- **Socket.IO client** in custom hooks
- **Global state updates** via Zustand stores
- **Component reactivity** through state subscriptions

### Routing Integration

Navigation through:

- **React Router** for page-level routing
- **Programmatic navigation** in component handlers
- **Route parameters** for dynamic content

---

**Next Steps**: Explore the [UI Design System](ui-design-system.md) documentation to understand how Shadcn/UI and Tailwind CSS are integrated throughout the component architecture.
