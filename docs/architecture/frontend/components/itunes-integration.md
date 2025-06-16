# iTunes Integration Architecture

## Overview

The iTunes integration provides direct frontend access to the iTunes Search API for metadata enhancement and discovery. This architecture eliminates server-side API proxying while providing rich metadata integration for song enhancement and library management.

## Current Implementation Status

**Primary Files**:
- `frontend/src/services/itunes.ts` - iTunes API client and types
- `frontend/src/hooks/useItunesSearch.ts` - Search and metadata hooks
- `frontend/src/components/metadata/ItunesSelector.tsx` - UI for iTunes results
- `frontend/src/types/ItunesTypes.ts` - Type definitions for iTunes data

**Status**: ✅ Complete and production-ready
**Architecture**: Direct frontend-to-iTunes API integration (no backend proxy)

## Core Responsibilities

### Metadata Discovery and Enhancement
- **Search Integration**: Real-time search of iTunes catalog during song creation
- **Metadata Enhancement**: Automatic population of song details from iTunes data
- **Cover Art Integration**: High-resolution album artwork retrieval and display
- **Rich Metadata**: Comprehensive song information including genre, release date, and track details

### Direct API Integration
- **CORS-Enabled Access**: Direct browser requests to iTunes Search API
- **Rate Limiting**: Client-side distributed rate limiting across users
- **Error Handling**: Comprehensive error handling for API failures
- **Caching Strategy**: Intelligent caching of search results and metadata

## Implementation Details

### iTunes API Client

```typescript
// iTunes API Service Implementation
export interface ItunesTrack {
  trackId: number;
  trackName: string;
  artistName: string;
  collectionName: string;
  artworkUrl100: string;
  artworkUrl600: string;
  previewUrl: string;
  trackTimeMillis: number;
  genre: string;
  releaseDate: string;
  explicit: boolean;
}

export class ItunesApiClient {
  private readonly baseUrl = 'https://itunes.apple.com/search';
  private readonly cache = new Map<string, ItunesSearchResponse>();

  async searchTracks(query: string, limit = 50): Promise<ItunesTrack[]> {
    const cacheKey = `${query}-${limit}`;

    // Check cache first
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!.results;
    }

    const params = new URLSearchParams({
      term: query,
      media: 'music',
      entity: 'song',
      limit: limit.toString(),
    });

    try {
      const response = await fetch(`${this.baseUrl}?${params}`);

      if (!response.ok) {
        throw new ItunesApiError(`API request failed: ${response.status}`);
      }

      const data: ItunesSearchResponse = await response.json();

      // Cache successful results
      this.cache.set(cacheKey, data);

      return data.results;
    } catch (error) {
      throw new ItunesApiError('Failed to search iTunes API', error);
    }
  }

  // High-resolution artwork URL generation
  getHighResArtwork(artworkUrl: string, size = 600): string {
    return artworkUrl.replace('100x100bb', `${size}x${size}bb`);
  }
}
```

### React Query Integration

```typescript
// Custom hooks for iTunes integration
export const useItunesSearch = (query: string, enabled = true) => {
  return useQuery({
    queryKey: ['itunes-search', query],
    queryFn: () => itunesClient.searchTracks(query),
    enabled: enabled && query.length > 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: (failureCount, error) => {
      // Retry logic for network errors but not API errors
      return failureCount < 2 && !(error instanceof ItunesApiError);
    },
  });
};

export const useItunesTrackById = (trackId: number) => {
  return useQuery({
    queryKey: ['itunes-track', trackId],
    queryFn: () => itunesClient.getTrackById(trackId),
    enabled: !!trackId,
    staleTime: 60 * 60 * 1000, // 1 hour - track data rarely changes
  });
};

// Enhanced metadata hook for song enhancement
export const useItunesEnhancement = (songTitle: string, artist: string) => {
  const searchQuery = `${artist} ${songTitle}`.trim();

  return useQuery({
    queryKey: ['itunes-enhancement', searchQuery],
    queryFn: async () => {
      const results = await itunesClient.searchTracks(searchQuery, 10);

      // Find best match based on similarity
      const bestMatch = findBestMatch(results, songTitle, artist);

      return bestMatch;
    },
    enabled: !!(songTitle && artist),
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
};
```

### Component Integration

```typescript
// iTunes Selection Component
interface ItunesSelectorProps {
  query: string;
  onSelect: (track: ItunesTrack) => void;
  selectedTrackId?: number;
}

export const ItunesSelector: React.FC<ItunesSelectorProps> = ({
  query,
  onSelect,
  selectedTrackId
}) => {
  const { data: tracks, isLoading, error } = useItunesSearch(query);

  if (isLoading) {
    return <ItunesSearchSkeleton />;
  }

  if (error) {
    return <ItunesErrorState error={error} />;
  }

  return (
    <div className="space-y-2">
      {tracks?.map((track) => (
        <ItunesTrackCard
          key={track.trackId}
          track={track}
          isSelected={track.trackId === selectedTrackId}
          onSelect={() => onSelect(track)}
        />
      ))}
    </div>
  );
};

// iTunes Track Card Component
const ItunesTrackCard: React.FC<{
  track: ItunesTrack;
  isSelected: boolean;
  onSelect: () => void;
}> = ({ track, isSelected, onSelect }) => {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md",
        isSelected && "ring-2 ring-primary"
      )}
      onClick={onSelect}
    >
      <CardContent className="flex gap-3 p-4">
        <img
          src={track.artworkUrl100}
          alt={`${track.collectionName} cover`}
          className="w-16 h-16 rounded-md object-cover"
        />
        <div className="flex-1 min-w-0">
          <h4 className="font-medium truncate">{track.trackName}</h4>
          <p className="text-sm text-muted-foreground truncate">
            {track.artistName}
          </p>
          <p className="text-sm text-muted-foreground truncate">
            {track.collectionName}
          </p>
          {track.previewUrl && (
            <ItunesPreviewPlayer previewUrl={track.previewUrl} />
          )}
        </div>
        <div className="text-right text-sm text-muted-foreground">
          <div>{formatDuration(track.trackTimeMillis)}</div>
          <div>{track.genre}</div>
        </div>
      </CardContent>
    </Card>
  );
};
```

## Integration Points

### Upload Workflow Integration
- **Automatic Enhancement**: Search iTunes during song upload for metadata
- **Manual Selection**: Allow users to choose from iTunes search results
- **Metadata Merging**: Intelligent merging of iTunes data with user input
- **Cover Art Selection**: High-resolution artwork integration

### Song Details Integration
- **Rich Metadata Display**: Show complete iTunes metadata in song details
- **Edit Functionality**: Allow changing iTunes association after creation
- **Preview Integration**: iTunes preview player within song details
- **Artwork Management**: iTunes artwork as primary cover art source

### Library Display Integration
- **Enhanced Listings**: Show iTunes-enhanced metadata in library views
- **Search Enhancement**: Use iTunes data for improved local search
- **Filtering Options**: Filter by iTunes metadata (genre, release year, etc.)
- **Visual Enhancement**: High-quality album artwork throughout the interface

## Design Patterns

### Direct API Access Pattern
The architecture eliminates backend proxying for several key benefits:

```typescript
// Direct frontend access pattern
const enhanceWithItunes = async (song: SongInput) => {
  // 1. Search iTunes directly from frontend
  const itunesResults = await itunesClient.searchTracks(
    `${song.artist} ${song.title}`
  );

  // 2. Let user select best match
  const selectedTrack = await userSelectItunesTrack(itunesResults);

  // 3. Enhance song metadata
  const enhancedSong = {
    ...song,
    itunesTrackId: selectedTrack.trackId,
    genre: selectedTrack.genre,
    album: selectedTrack.collectionName,
    coverArt: selectedTrack.artworkUrl600,
    duration: selectedTrack.trackTimeMillis / 1000,
  };

  // 4. Save enhanced song to backend
  return await saveSongToBackend(enhancedSong);
};
```

### Caching Strategy
- **Search Results**: Cache search results for 5 minutes
- **Track Details**: Cache individual track data for 1 hour
- **Artwork URLs**: Cache artwork URLs permanently (they don't change)
- **Error Responses**: Don't cache error responses to allow retry

### Error Handling Strategy
- **Network Errors**: Automatic retry with exponential backoff
- **API Rate Limiting**: Graceful degradation with user notification
- **CORS Issues**: Fallback messaging with manual entry option
- **Invalid Results**: Filter out incomplete or invalid iTunes data

## Dependencies

### External Services
- **iTunes Search API**: Apple's public search API for music metadata
- **Image CDN**: iTunes artwork URLs (managed by Apple)

### Frontend Libraries
- **TanStack Query**: API state management and caching
- **Fetch API**: Native browser HTTP client
- **React**: Component framework

### Internal Dependencies
- **Error Handling**: Global error boundary integration
- **Loading States**: Shared skeleton and loading components
- **Type System**: Comprehensive TypeScript types for iTunes data

## Performance Considerations

### Search Optimization
- **Debounced Search**: Prevent excessive API calls during typing
- **Smart Caching**: Cache results to minimize repeat requests
- **Result Limiting**: Limit search results to improve response times
- **Prefetching**: Prefetch common searches and popular tracks

### Network Efficiency
- **Request Batching**: Batch multiple track lookups when possible
- **Compression**: Leverage browser compression for API responses
- **CDN Benefits**: iTunes artwork served from Apple's global CDN
- **Offline Handling**: Graceful degradation when iTunes API unavailable

### User Experience
- **Progressive Loading**: Show partial results as they arrive
- **Background Updates**: Update metadata in background without blocking UI
- **Error Recovery**: Clear paths for manual metadata entry when API fails
- **Responsive Design**: Optimized for mobile network conditions

## Security Considerations

### API Security
- **CORS Protection**: iTunes API properly configured for browser access
- **No Sensitive Data**: No API keys or secrets required
- **Rate Limiting**: Client-side rate limiting to prevent abuse
- **Input Validation**: Sanitize search queries before API calls

### Data Privacy
- **No User Data**: Search queries not stored or tracked
- **Apple Privacy**: Leverages Apple's privacy-focused API design
- **Local Storage**: Minimal local storage of search results

## Future Enhancements

### Enhanced Metadata
- **Additional Sources**: Integration with other metadata providers
- **Machine Learning**: AI-powered best match selection
- **Custom Metadata**: User-contributed metadata improvements
- **Batch Processing**: Bulk metadata enhancement for existing library

### Advanced Features
- **Smart Suggestions**: Contextual search suggestions based on user library
- **Metadata Verification**: Community-driven metadata accuracy improvements
- **Integration Expansion**: iTunes Store links and purchase integration
- **Analytics**: Track metadata enhancement success rates

---

**Architecture Benefits**: This direct frontend integration approach eliminates the complexity and reliability issues of server-side API proxying while providing users with immediate access to rich, high-quality metadata from Apple's comprehensive music catalog.
