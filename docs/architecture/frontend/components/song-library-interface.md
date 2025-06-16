# Song Library Interface - Open Karaoke Studio Frontend

**Last Updated**: June 15, 2025  
**Status**: Implemented  
**Components**: LibraryPage • ArtistAccordion • SongGrid • SearchInterface • LibraryFilters

## 🎯 Overview

The Song Library Interface provides the primary browsing experience for the karaoke song collection. The interface uses an artist-accordion pattern that scales efficiently as the library grows, combined with comprehensive search and filtering capabilities for both desktop and mobile usage patterns.

## 🏗️ Architecture Overview

### Component Hierarchy
```
LibraryPage (Main Container)
├── SearchInterface (Real-time search)
├── LibraryFilters (Genre, source, sorting)
├── LibraryStats (Song count, new additions)
├── ArtistAccordion (Collapsible artist groups)
│   ├── ArtistSection (Individual artist)
│   │   ├── ArtistHeader (Artist name, song count)
│   │   └── SongGrid (Songs by artist)
│   │       └── SongCard (Individual songs)
└── SongDetailsDialog (Song details overlay)
```

### Key Design Principles
- **Performance First** - Lazy loading and virtualization for large libraries
- **Artist-Centric Browsing** - Natural grouping matches user mental models  
- **Unified Search** - Real-time filtering across all content
- **Mobile-Ready** - Touch-friendly interface for party mode usage
- **Scalable Architecture** - Efficient at 100 songs or 10,000 songs

## 🎵 Core Components

### LibraryPage
**File**: `/frontend/src/pages/LibraryPage.tsx`

Main container that orchestrates the library browsing experience:

```typescript
function LibraryPage() {
  const { data: songs, isLoading, error } = useSongs.useAllSongs();
  const { data: artists } = useArtists();
  const { filters, setFilters, selectedSong, setSelectedSong } = useSongsStore();
  const { searchTerm, debouncedSearchTerm, setSearchTerm } = useDebouncedSearch();
  
  // Filter songs based on current filters and search
  const filteredSongs = useMemo(() => {
    if (!songs) return [];
    
    return songs.filter(song => {
      // Search filter
      if (debouncedSearchTerm) {
        const searchLower = debouncedSearchTerm.toLowerCase();
        if (!song.title.toLowerCase().includes(searchLower) &&
            !song.artist.toLowerCase().includes(searchLower) &&
            !song.album?.toLowerCase().includes(searchLower)) {
          return false;
        }
      }
      
      // Genre filter
      if (filters.genre && song.genre !== filters.genre) {
        return false;
      }
      
      // Source filter
      if (filters.source !== 'all') {
        if (filters.source === 'itunes' && !song.itunesId) return false;
        if (filters.source === 'youtube' && !song.youtubeId) return false;
      }
      
      return true;
    });
  }, [songs, debouncedSearchTerm, filters]);
  
  // Group songs by artist for accordion display
  const songsByArtist = useMemo(() => {
    const grouped = filteredSongs.reduce((acc, song) => {
      const artist = song.artist;
      if (!acc[artist]) {
        acc[artist] = [];
      }
      acc[artist].push(song);
      return acc;
    }, {} as Record<string, Song[]>);
    
    // Sort artists alphabetically and sort songs within each artist
    const sortedArtists = Object.keys(grouped).sort();
    return sortedArtists.map(artist => ({
      artist,
      songs: grouped[artist].sort((a, b) => a.title.localeCompare(b.title)),
    }));
  }, [filteredSongs]);
  
  if (error) {
    return (
      <div className="container mx-auto px-4 py-6">
        <ErrorBoundary message="Failed to load song library" onRetry={() => window.location.reload()} />
      </div>
    );
  }
  
  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Song Library</h1>
            <p className="text-muted-foreground">
              {filteredSongs.length} of {songs?.length || 0} songs
            </p>
          </div>
          
          <LibraryStats songs={songs} />
        </div>
        
        {/* Search and filters */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <SearchInterface 
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Search songs, artists, or albums..."
            />
          </div>
          <LibraryFilters 
            filters={filters}
            onFiltersChange={setFilters}
          />
        </div>
      </div>
      
      {/* Main content */}
      {isLoading ? (
        <LibrarySkeleton />
      ) : songsByArtist.length === 0 ? (
        <EmptyLibraryState 
          hasFilters={!!debouncedSearchTerm || filters.genre || filters.source !== 'all'}
          onClearFilters={() => {
            setSearchTerm('');
            setFilters({ search: '', genre: null, source: 'all' });
          }}
        />
      ) : (
        <ArtistAccordion 
          artistGroups={songsByArtist}
          onSongSelect={setSelectedSong}
        />
      )}
      
      {/* Song details dialog */}
      <SongDetailsDialog
        song={selectedSong}
        open={!!selectedSong}
        onClose={() => setSelectedSong(null)}
      />
    </div>
  );
}
```

### ArtistAccordion
**File**: `/frontend/src/components/library/ArtistAccordion.tsx`

Collapsible artist groups with lazy-loaded song content:

```typescript
interface ArtistGroup {
  artist: string;
  songs: Song[];
}

interface ArtistAccordionProps {
  artistGroups: ArtistGroup[];
  onSongSelect: (song: Song) => void;
}

function ArtistAccordion({ artistGroups, onSongSelect }: ArtistAccordionProps) {
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(new Set());
  
  const toggleArtist = useCallback((artist: string) => {
    setExpandedArtists(prev => {
      const next = new Set(prev);
      if (next.has(artist)) {
        next.delete(artist);
      } else {
        next.add(artist);
      }
      return next;
    });
  }, []);
  
  return (
    <div className="space-y-2">
      {artistGroups.map(({ artist, songs }) => (
        <ArtistSection
          key={artist}
          artist={artist}
          songs={songs}
          isExpanded={expandedArtists.has(artist)}
          onToggle={() => toggleArtist(artist)}
          onSongSelect={onSongSelect}
        />
      ))}
    </div>
  );
}
```

### ArtistSection
**File**: `/frontend/src/components/library/ArtistSection.tsx`

Individual artist section with collapsible song grid:

```typescript
interface ArtistSectionProps {
  artist: string;
  songs: Song[];
  isExpanded: boolean;
  onToggle: () => void;
  onSongSelect: (song: Song) => void;
}

function ArtistSection({ artist, songs, isExpanded, onToggle, onSongSelect }: ArtistSectionProps) {
  return (
    <Card className="overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-4 text-left hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset"
        aria-expanded={isExpanded}
        aria-controls={`artist-${artist}-content`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-rust to-orange-peel flex items-center justify-center">
              <span className="text-lemon-chiffon font-bold text-lg">
                {artist.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h3 className="font-semibold text-foreground text-lg">{artist}</h3>
              <p className="text-sm text-muted-foreground">
                {songs.length} song{songs.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Quick stats */}
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
              {songs.some(s => s.itunesId) && (
                <Badge variant="outline" className="text-xs">iTunes</Badge>
              )}
              {songs.some(s => s.youtubeId) && (
                <Badge variant="outline" className="text-xs">YouTube</Badge>
              )}
            </div>
            
            <ChevronDown 
              className={cn(
                "h-5 w-5 text-muted-foreground transition-transform duration-200",
                isExpanded && "transform rotate-180"
              )}
            />
          </div>
        </div>
      </button>
      
      <Collapsible open={isExpanded}>
        <CollapsibleContent 
          id={`artist-${artist}-content`}
          className="border-t border-border"
        >
          <div className="p-4">
            <SongGrid 
              songs={songs}
              onSongSelect={onSongSelect}
              variant="compact"
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
```

### SearchInterface
**File**: `/frontend/src/components/library/SearchInterface.tsx`

Real-time search with advanced filtering capabilities:

```typescript
interface SearchInterfaceProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function SearchInterface({ value, onChange, placeholder = "Search..." }: SearchInterfaceProps) {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Keyboard shortcut for search focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        inputRef.current?.focus();
      }
      
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        inputRef.current?.blur();
        onChange('');
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onChange]);
  
  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="pl-10 pr-8"
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      
      {/* Search shortcut hint */}
      {!isFocused && !value && (
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
          <Badge variant="outline" className="text-xs">
            /
          </Badge>
        </div>
      )}
      
      {/* Search suggestions could go here in the future */}
    </div>
  );
}
```

### LibraryFilters
**File**: `/frontend/src/components/library/LibraryFilters.tsx`

Comprehensive filtering controls for the library:

```typescript
interface LibraryFiltersProps {
  filters: {
    genre: string | null;
    source: 'all' | 'itunes' | 'youtube';
  };
  onFiltersChange: (filters: Partial<LibraryFiltersProps['filters']>) => void;
}

function LibraryFilters({ filters, onFiltersChange }: LibraryFiltersProps) {
  const { data: genres } = useGenres();
  
  return (
    <div className="flex flex-wrap gap-2">
      {/* Genre filter */}
      <Select
        value={filters.genre || ''}
        onValueChange={(value) => 
          onFiltersChange({ genre: value || null })
        }
      >
        <SelectTrigger className="w-32">
          <SelectValue placeholder="Genre" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All Genres</SelectItem>
          {genres?.map((genre) => (
            <SelectItem key={genre} value={genre}>
              {genre}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      {/* Source filter */}
      <Select
        value={filters.source}
        onValueChange={(value) => 
          onFiltersChange({ source: value as 'all' | 'itunes' | 'youtube' })
        }
      >
        <SelectTrigger className="w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Sources</SelectItem>
          <SelectItem value="itunes">iTunes Only</SelectItem>
          <SelectItem value="youtube">YouTube Only</SelectItem>
        </SelectContent>
      </Select>
      
      {/* Clear filters button */}
      {(filters.genre || filters.source !== 'all') && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onFiltersChange({ genre: null, source: 'all' })}
          className="px-2"
        >
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
```

## 🔄 User Experience Patterns

### Progressive Disclosure
The interface reveals information progressively to avoid overwhelming users:

1. **Initial View** - Artist list with song counts
2. **Artist Expansion** - Songs for selected artist
3. **Song Selection** - Detailed song information in dialog
4. **Action Selection** - Play, queue, or close options

### Search and Filter Integration
```typescript
// Unified search that works across all content
const searchableFields = ['title', 'artist', 'album', 'genre'];

function filterSongs(songs: Song[], searchTerm: string, filters: LibraryFilters) {
  return songs.filter(song => {
    // Text search across multiple fields
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = searchableFields.some(field => 
        song[field]?.toLowerCase().includes(searchLower)
      );
      if (!matchesSearch) return false;
    }
    
    // Genre filter
    if (filters.genre && song.genre !== filters.genre) {
      return false;
    }
    
    // Source filter
    if (filters.source === 'itunes' && !song.itunesId) return false;
    if (filters.source === 'youtube' && !song.youtubeId) return false;
    
    return true;
  });
}
```

### Keyboard Navigation
Desktop users can navigate efficiently with keyboard shortcuts:

```typescript
// Global keyboard shortcuts
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Focus search with '/' key
    if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      searchInputRef.current?.focus();
    }
    
    // Clear search with Escape
    if (e.key === 'Escape') {
      setSearchTerm('');
      searchInputRef.current?.blur();
    }
    
    // Navigate artists with arrow keys (when search not focused)
    if (document.activeElement !== searchInputRef.current) {
      if (e.key === 'ArrowDown') {
        // Navigate to next artist
      }
      if (e.key === 'ArrowUp') {
        // Navigate to previous artist
      }
      if (e.key === 'Enter' || e.key === ' ') {
        // Toggle current artist expansion
      }
    }
  };
  
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, []);
```

## 📱 Mobile Optimization

### Touch-Friendly Interface
- **Large Touch Targets** - Artist headers and buttons sized for finger interaction
- **Swipe Gestures** - Planned support for swipe-to-expand artists
- **Thumb Navigation** - Important actions within thumb reach
- **Minimal Typing** - Browse-first approach reduces keyboard dependency

### Responsive Grid Layout
```typescript
// Adaptive song grid based on screen size
function SongGrid({ songs, variant = "default" }: SongGridProps) {
  const gridClasses = cn(
    "grid gap-4",
    variant === "compact" 
      ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" 
      : "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
  );
  
  return (
    <div className={gridClasses}>
      {songs.map(song => (
        <SongCard 
          key={song.id} 
          song={song} 
          variant={variant}
          onSelect={onSongSelect}
        />
      ))}
    </div>
  );
}
```

### Progressive Loading Strategy
```typescript
// Virtualized loading for large artist lists
function VirtualizedArtistList({ artists }: VirtualizedArtistListProps) {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 });
  
  const visibleArtists = useMemo(() => 
    artists.slice(visibleRange.start, visibleRange.end),
    [artists, visibleRange]
  );
  
  return (
    <div className="space-y-2">
      {visibleArtists.map(artist => (
        <ArtistSection key={artist.name} artist={artist} />
      ))}
      
      {visibleRange.end < artists.length && (
        <Button 
          variant="outline" 
          onClick={() => setVisibleRange(prev => ({ 
            ...prev, 
            end: prev.end + 20 
          }))}
          className="w-full"
        >
          Load More Artists
        </Button>
      )}
    </div>
  );
}
```

## 🚀 Performance Optimizations

### Lazy Loading Strategy
- **Artist Content** - Songs only loaded when artist is expanded
- **Image Loading** - Album artwork loaded on demand
- **Virtualization** - Large lists use virtual scrolling
- **Debounced Search** - Reduces API calls during typing

### Caching Strategy
```typescript
// Intelligent caching with TanStack Query
export function useArtistSongs(artist: string, enabled = false) {
  return useQuery({
    queryKey: ['songs', 'by-artist', artist],
    queryFn: () => apiGet<Song[]>(`songs/by-artist/${encodeURIComponent(artist)}`),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
  });
}

// Prefetch on hover for better perceived performance
function ArtistHeader({ artist, onExpand }: ArtistHeaderProps) {
  const queryClient = useQueryClient();
  
  const handleMouseEnter = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['songs', 'by-artist', artist],
      queryFn: () => apiGet<Song[]>(`songs/by-artist/${encodeURIComponent(artist)}`),
    });
  }, [artist, queryClient]);
  
  return (
    <button 
      onMouseEnter={handleMouseEnter}
      onClick={onExpand}
    >
      {/* Artist header content */}
    </button>
  );
}
```

### Memory Management
```typescript
// Clean up expanded artists when search changes
useEffect(() => {
  if (searchTerm) {
    setExpandedArtists(new Set());
  }
}, [searchTerm]);

// Limit concurrent expanded artists to prevent memory issues
const maxExpandedArtists = 5;

const toggleArtist = useCallback((artist: string) => {
  setExpandedArtists(prev => {
    const next = new Set(prev);
    
    if (next.has(artist)) {
      next.delete(artist);
    } else {
      // If at limit, remove oldest expanded artist
      if (next.size >= maxExpandedArtists) {
        const [oldest] = next;
        next.delete(oldest);
      }
      next.add(artist);
    }
    
    return next;
  });
}, []);
```

## 🧪 Testing Strategy

### Component Testing
```typescript
describe('LibraryPage', () => {
  it('filters songs based on search term', async () => {
    const mockSongs = [
      createMockSong({ title: 'Rock Song', artist: 'Rock Band' }),
      createMockSong({ title: 'Jazz Song', artist: 'Jazz Band' }),
    ];
    
    render(<LibraryPage />, {
      wrapper: ({ children }) => (
        <QueryClient client={queryClient}>
          {children}
        </QueryClient>
      ),
    });
    
    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'rock' } });
    
    await waitFor(() => {
      expect(screen.getByText('Rock Song')).toBeInTheDocument();
      expect(screen.queryByText('Jazz Song')).not.toBeInTheDocument();
    });
  });
});
```

### Performance Testing
```typescript
// Test virtualization performance
describe('Large Library Performance', () => {
  it('handles 1000+ songs efficiently', async () => {
    const largeSongList = Array.from({ length: 1000 }, (_, i) => 
      createMockSong({ title: `Song ${i}` })
    );
    
    const startTime = performance.now();
    render(<LibraryPage songs={largeSongList} />);
    const renderTime = performance.now() - startTime;
    
    expect(renderTime).toBeLessThan(100); // Should render in under 100ms
  });
});
```

---

**Summary**: The Song Library Interface provides a scalable, user-friendly browsing experience that handles libraries of any size. The artist-accordion pattern, combined with real-time search and filtering, creates an efficient navigation system that works well on both desktop and mobile devices.

**Next Steps**: Explore the [Upload Workflow](upload-workflow.md) to understand how new songs are added to the library, or check out the [Queue Management System](queue-management-system.md) for how selected songs move into the karaoke experience.
