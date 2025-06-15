import { useApiQuery } from './useApi';
import { Song } from '../types/Song';

// Query keys for React Query
const ARTIST_QUERY_KEYS = {
  artists: (params: ArtistListParams) => ['artists', params] as const,
  artistSongs: (artist: string, params: ArtistSongsParams) => ['artists', artist, 'songs', params] as const,
  search: (params: SearchParams) => ['songs', 'search', params] as const,
};

// Types for API parameters
interface ArtistListParams {
  search?: string;
  limit?: number;
  offset?: number;
}

interface ArtistSongsParams {
  limit?: number;
  offset?: number;
  sort?: 'title' | 'album' | 'year' | 'dateAdded';
  direction?: 'asc' | 'desc';
}

interface SearchParams {
  q: string;
  limit?: number;
  offset?: number;
  groupByArtist?: boolean;
  sort?: 'relevance' | 'title' | 'artist' | 'dateAdded';
  direction?: 'asc' | 'desc';
}

// API Response Types
interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface PaginationInfo {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

interface ArtistListResponse {
  artists: Artist[];
  pagination: PaginationInfo;
}

interface ArtistSongsResponse {
  songs: Song[];
  artist: string;
  pagination: PaginationInfo;
}

interface SearchResponse {
  songs?: Song[];
  artists?: Array<{
    artist: string;
    songCount: number;
    songs: Song[];
  }>;
  totalSongs?: number;
  totalArtists?: number;
  pagination: PaginationInfo;
}

/**
 * Hook for managing paginated library browsing
 */
export function useLibraryBrowsing() {
  
  /**
   * Get paginated list of artists
   */
  const useArtists = (params: ArtistListParams = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.set('search', params.search);
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.offset) queryParams.set('offset', params.offset.toString());
    
    return useApiQuery<ArtistListResponse, typeof ARTIST_QUERY_KEYS.artists>(
      ARTIST_QUERY_KEYS.artists(params),
      `songs/artists?${queryParams.toString()}`,
      {
        enabled: true,
        staleTime: 5 * 60 * 1000, // 5 minutes - artists don't change often
      }
    );
  };

  /**
   * Get paginated songs for a specific artist
   */
  const useArtistSongs = (artist: string, params: ArtistSongsParams = {}) => {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.offset) queryParams.set('offset', params.offset.toString());
    if (params.sort) queryParams.set('sort', params.sort);
    if (params.direction) queryParams.set('direction', params.direction);

    return useApiQuery<ArtistSongsResponse, typeof ARTIST_QUERY_KEYS.artistSongs>(
      ARTIST_QUERY_KEYS.artistSongs(artist, params),
      `songs/by-artist/${encodeURIComponent(artist)}?${queryParams.toString()}`,
      {
        enabled: !!artist,
        staleTime: 2 * 60 * 1000, // 2 minutes
      }
    );
  };

  /**
   * Search songs with pagination
   */
  const useSearchSongs = (params: SearchParams) => {
    const queryParams = new URLSearchParams();
    queryParams.set('q', params.q);
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.offset) queryParams.set('offset', params.offset.toString());
    if (params.groupByArtist) queryParams.set('group_by_artist', 'true');
    if (params.sort) queryParams.set('sort', params.sort);
    if (params.direction) queryParams.set('direction', params.direction);

    return useApiQuery<SearchResponse, typeof ARTIST_QUERY_KEYS.search>(
      ARTIST_QUERY_KEYS.search(params),
      `songs/search?${queryParams.toString()}`,
      {
        enabled: !!params.q.trim(),
        staleTime: 30 * 1000, // 30 seconds - search results can change
      }
    );
  };

  return {
    useArtists,
    useArtistSongs,
    useSearchSongs,
  };
}
