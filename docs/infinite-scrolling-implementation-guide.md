# Infinite Scrolling Implementation Guide

## Overview

This guide covers implementing infinite scrolling for the Open Karaoke Studio project, building on the existing pagination infrastructure. Infinite scrolling provides a seamless user experience by automatically loading content as users scroll, eliminating the need for "Load More" buttons.

## Current Architecture

The project already has a solid foundation for infinite scrolling:

- **Backend**: Paginated API endpoints with `limit` and `offset` parameters
- **Frontend**: React Query hooks with pagination state management
- **Components**: Accordion pattern with lazy loading

## Implementation Approaches

### 1. Intersection Observer (Recommended)

The modern, performant approach using the browser's native Intersection Observer API.

#### Hook Implementation

```typescript
// filepath: frontend/src/hooks/useInfiniteScroll.ts
import { useEffect, useRef, useCallback } from 'react';

interface UseInfiniteScrollProps {
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  threshold?: number;
  rootMargin?: string;
}

export const useInfiniteScroll = ({
  loading,
  hasMore,
  onLoadMore,
  threshold = 0.1,
  rootMargin = '100px',
}: UseInfiniteScrollProps) => {
  const sentinelRef = useRef<HTMLDivElement>(null);

  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loading) {
        onLoadMore();
      }
    },
    [hasMore, loading, onLoadMore]
  );

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(handleIntersect, {
      threshold,
      rootMargin,
    });

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [handleIntersect, threshold, rootMargin]);

  return sentinelRef;
};
```

#### Enhanced Library Browsing Hook

```typescript
// filepath: frontend/src/hooks/useInfiniteLibraryBrowsing.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';

interface InfiniteArtistsResult {
  artists: Artist[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isLoading: boolean;
  error: Error | null;
}

export const useInfiniteArtists = (
  searchTerm: string = '',
  pageSize: number = 20
): InfiniteArtistsResult => {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['artists', 'infinite', { search: searchTerm, pageSize }],
    queryFn: ({ pageParam = 0 }) =>
      fetchArtists({
        search: searchTerm,
        limit: pageSize,
        offset: pageParam * pageSize,
      }),
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.pagination.hasMore) return undefined;
      return allPages.length;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const artists = useMemo(() => {
    return data?.pages.flatMap(page => page.artists) ?? [];
  }, [data]);

  return {
    artists,
    hasNextPage: hasNextPage ?? false,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    error: error as Error | null,
  };
};
```

### 2. Infinite Artist Accordion Component

```typescript
// filepath: frontend/src/components/library/InfiniteArtistAccordion.tsx
import React, { useState } from 'react';
import { useInfiniteArtists } from '@/hooks/useInfiniteLibraryBrowsing';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import ArtistSection from './ArtistSection';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import vintageTheme from '@/utils/theme';

interface InfiniteArtistAccordionProps {
  searchTerm?: string;
  onSongSelect?: (song: Song) => void;
  onToggleFavorite?: (song: Song) => void;
  onAddToQueue?: (song: Song) => void;
}

const InfiniteArtistAccordion: React.FC<InfiniteArtistAccordionProps> = ({
  searchTerm = '',
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
}) => {
  const colors = vintageTheme.colors;
  const [expandedArtists, setExpandedArtists] = useState<Set<string>>(new Set());

  const {
    artists,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    error,
  } = useInfiniteArtists(searchTerm);

  // Infinite scroll hook
  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: '200px', // Start loading when 200px away
  });

  const toggleArtist = (artistName: string) => {
    setExpandedArtists(prev => {
      const newSet = new Set(prev);
      if (newSet.has(artistName)) {
        newSet.delete(artistName);
      } else {
        newSet.add(artistName);
      }
      return newSet;
    });
  };

  // Group artists alphabetically
  const groupedArtists = React.useMemo(() => {
    return artists.reduce((groups, artist) => {
      const letter = artist.firstLetter;
      if (!groups[letter]) {
        groups[letter] = [];
      }
      groups[letter].push(artist);
      return groups;
    }, {} as Record<string, typeof artists>);
  }, [artists]);

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-500">Error loading artists</div>
        <div className="text-sm opacity-60">{error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 animate-pulse rounded" />
          ))}
        </div>
      ) : (
        <>
          {/* Alphabetical artist sections */}
          {Object.entries(groupedArtists).map(([letter, artists]) => (
            <div key={letter}>
              <div
                className="sticky top-0 px-3 py-2 mb-3 font-bold text-lg border-b"
                style={{
                  backgroundColor: colors.darkCyan,
                  color: colors.orangePeel,
                  borderColor: colors.orangePeel,
                  zIndex: 10
                }}
              >
                {letter}
              </div>

              <div className="space-y-2">
                {artists.map((artist) => (
                  <ArtistSection
                    key={artist.name}
                    artistName={artist.name}
                    songCount={artist.songCount}
                    isExpanded={expandedArtists.has(artist.name)}
                    onToggle={() => toggleArtist(artist.name)}
                    onSongSelect={onSongSelect}
                    onToggleFavorite={onToggleFavorite}
                    onAddToQueue={onAddToQueue}
                  />
                ))}
              </div>
            </div>
          ))}

          {/* Intersection Observer Sentinel */}
          <div ref={sentinelRef} className="h-4">
            {isFetchingNextPage && (
              <div className="flex justify-center py-4">
                <LoadingSpinner />
                <span className="ml-2 text-sm opacity-60">Loading more artists...</span>
              </div>
            )}
          </div>

          {/* End of results indicator */}
          {!hasNextPage && artists.length > 0 && (
            <div className="text-center py-4 text-sm opacity-60">
              All artists loaded ({artists.length} total)
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default InfiniteArtistAccordion;
```

### 3. Infinite Songs Within Artist Sections

For songs within each artist accordion, implement a similar pattern:

```typescript
// Enhanced ArtistSection with infinite scrolling
const useInfiniteArtistSongs = (artistName: string, pageSize: number = 10) => {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['artist-songs', 'infinite', artistName, { pageSize }],
    queryFn: ({ pageParam = 0 }) =>
      fetchSongsByArtist(artistName, {
        limit: pageSize,
        offset: pageParam * pageSize,
        sort: 'title',
        direction: 'asc',
      }),
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.pagination.hasMore) return undefined;
      return allPages.length;
    },
    enabled: !!artistName,
  });

  const songs = useMemo(() => {
    return data?.pages.flatMap(page => page.songs) ?? [];
  }, [data]);

  return {
    songs,
    hasNextPage: hasNextPage ?? false,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    error: error as Error | null,
  };
};
```

## Performance Optimizations

### 1. Virtual Scrolling (For Large Lists)

For extremely large datasets (10,000+ items), consider implementing virtual scrolling:

```typescript
// Using react-window or react-virtualized
import { FixedSizeList as List } from 'react-window';
import InfiniteLoader from 'react-window-infinite-loader';

const VirtualizedArtistList = ({ artists, loadMoreItems, hasNextPage }) => {
  const itemCount = hasNextPage ? artists.length + 1 : artists.length;
  const isItemLoaded = index => !!artists[index];

  return (
    <InfiniteLoader
      isItemLoaded={isItemLoaded}
      itemCount={itemCount}
      loadMoreItems={loadMoreItems}
    >
      {({ onItemsRendered, ref }) => (
        <List
          ref={ref}
          height={600}
          itemCount={itemCount}
          itemSize={80}
          onItemsRendered={onItemsRendered}
        >
          {({ index, style }) => (
            <div style={style}>
              {artists[index] ? (
                <ArtistSection artist={artists[index]} />
              ) : (
                <LoadingPlaceholder />
              )}
            </div>
          )}
        </List>
      )}
    </InfiniteLoader>
  );
};
```

### 2. Debounced Search

For search functionality with infinite scroll:

```typescript
import { useDebouncedValue } from '@/hooks/useDebouncedValue';

const SearchableInfiniteArtists = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebouncedValue(searchTerm, 300);

  const { artists, fetchNextPage, hasNextPage } = useInfiniteArtists(debouncedSearch);

  return (
    <div>
      <SearchInput
        value={searchTerm}
        onChange={setSearchTerm}
        placeholder="Search artists..."
      />
      <InfiniteArtistAccordion searchTerm={debouncedSearch} />
    </div>
  );
};
```

### 3. Optimistic Updates

For better UX when toggling favorites or adding to queue:

```typescript
const { mutate: toggleFavorite } = useMutation({
  mutationFn: (song: Song) => api.toggleFavorite(song.id),
  onMutate: async (song) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries(['artist-songs', song.artistName]);

    // Snapshot previous value
    const previousSongs = queryClient.getQueryData(['artist-songs', song.artistName]);

    // Optimistically update
    queryClient.setQueryData(['artist-songs', song.artistName], (old) => {
      // Update the song in the cached data
      return updateSongInCache(old, song.id, { isFavorite: !song.isFavorite });
    });

    return { previousSongs };
  },
  onError: (err, song, context) => {
    // Rollback on error
    queryClient.setQueryData(['artist-songs', song.artistName], context.previousSongs);
  },
  onSettled: (data, error, song) => {
    // Always refetch after error or success
    queryClient.invalidateQueries(['artist-songs', song.artistName]);
  },
});
```

## Implementation Checklist

### Phase 1: Basic Infinite Scroll
- [ ] Create `useInfiniteScroll` hook with Intersection Observer
- [ ] Implement `useInfiniteArtists` hook with React Query
- [ ] Build `InfiniteArtistAccordion` component
- [ ] Test with medium-sized library (100-500 artists)

### Phase 2: Enhanced Features
- [ ] Add infinite scrolling to songs within artist sections
- [ ] Implement debounced search with infinite scroll
- [ ] Add loading states and error handling
- [ ] Optimize re-renders with React.memo

### Phase 3: Performance Optimization
- [ ] Add virtual scrolling for very large datasets
- [ ] Implement optimistic updates for user actions
- [ ] Add prefetching for next pages
- [ ] Performance testing with large libraries (1000+ artists)

### Phase 4: Mobile Experience
- [ ] Touch-optimized scrolling
- [ ] Pull-to-refresh functionality
- [ ] Gesture handling for expand/collapse
- [ ] iOS/Android-specific optimizations

## Best Practices

### 1. Memory Management
```typescript
// Limit the number of pages in memory
const MAX_PAGES = 10;

const useInfiniteArtistsWithMemoryLimit = (searchTerm: string) => {
  const query = useInfiniteQuery({
    // ... other options
    onSuccess: (data) => {
      // Keep only the last MAX_PAGES pages
      if (data.pages.length > MAX_PAGES) {
        queryClient.setQueryData(
          query.queryKey,
          {
            ...data,
            pages: data.pages.slice(-MAX_PAGES),
            pageParams: data.pageParams.slice(-MAX_PAGES),
          }
        );
      }
    },
  });

  return query;
};
```

### 2. Error Recovery
```typescript
const { retry, error, isError } = useInfiniteArtists(searchTerm);

// Show retry button on error
{isError && (
  <div className="text-center py-4">
    <p className="text-red-500 mb-2">Failed to load artists</p>
    <Button onClick={() => retry()}>Try Again</Button>
  </div>
)}
```

### 3. Accessibility
```typescript
// Add ARIA labels for screen readers
<div
  ref={sentinelRef}
  aria-live="polite"
  aria-label={isFetchingNextPage ? "Loading more content" : "End of list"}
  className="h-4"
>
  {isFetchingNextPage && <LoadingSpinner />}
</div>
```

## Migration from Current Implementation

To migrate from the current "Load More" button approach:

1. **Keep Both Approaches**: Implement infinite scroll as an option, allowing users to choose
2. **A/B Testing**: Test infinite scroll with a subset of users
3. **Graceful Fallback**: Fall back to "Load More" buttons if Intersection Observer is not supported
4. **User Preference**: Add a setting to let users choose their preferred loading method

## Testing Strategy

### 1. Unit Tests
```typescript
// Test the infinite scroll hook
describe('useInfiniteScroll', () => {
  it('should call onLoadMore when sentinel is intersecting', () => {
    const onLoadMore = jest.fn();
    renderHook(() => useInfiniteScroll({
      loading: false,
      hasMore: true,
      onLoadMore,
    }));

    // Mock intersection observer behavior
    // Assert onLoadMore is called
  });
});
```

### 2. Integration Tests
- Test with various library sizes
- Test search functionality
- Test error states and recovery
- Test on different devices and browsers

### 3. Performance Tests
- Measure scroll performance with large datasets
- Test memory usage over time
- Benchmark against current "Load More" approach

This guide provides a comprehensive approach to implementing infinite scrolling while maintaining the existing architecture and ensuring good performance and user experience.
