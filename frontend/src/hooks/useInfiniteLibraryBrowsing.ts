import { useInfiniteQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Song } from '../types/Song';

// Helper function for API calls
const apiGet = async <T>(url: string): Promise<T> => {
  const response = await fetch(`/api/${url}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`HTTP error! Status: ${response.status}`);
  }
  return response.json();
};

// Types (reusing from useLibraryBrowsing.ts)
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

interface InfiniteArtistsResult {
  artists: Artist[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isLoading: boolean;
  error: Error | null;
}

interface InfiniteArtistSongsResult {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isLoading: boolean;
  error: Error | null;
}

/**
 * Hook for infinite scrolling through artists
 * 
 * @param searchTerm - Optional search term to filter artists
 * @param pageSize - Number of artists to fetch per page (default: 200)
 *                   High limit is efficient since we only fetch lightweight artist metadata,
 *                   not song data. Songs are lazy-loaded when artists are expanded.
 */
export const useInfiniteArtists = (
  searchTerm: string = '',
  pageSize: number = 200
): InfiniteArtistsResult => {
  const fetchArtists = async ({ pageParam = 0 }) => {
    const queryParams = new URLSearchParams();
    if (searchTerm) queryParams.set('search', searchTerm);
    queryParams.set('limit', pageSize.toString());
    queryParams.set('offset', (pageParam * pageSize).toString());
    
    return apiGet<ArtistListResponse>(`songs/artists?${queryParams.toString()}`);
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['artists', 'infinite', { search: searchTerm, pageSize }],
    queryFn: fetchArtists,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    initialPageParam: 0,
  });

  const artists = useMemo(() => {
    return data?.pages.flatMap(page => page?.artists ?? []).filter(Boolean) ?? [];
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

export const useInfiniteArtistSongs = (
  artistName: string,
  pageSize: number = 10,
  options: { enabled?: boolean } = {}
): InfiniteArtistSongsResult => {
  const fetchSongsByArtist = async ({ pageParam = 0 }) => {
    const queryParams = new URLSearchParams();
    queryParams.set('limit', pageSize.toString());
    queryParams.set('offset', (pageParam * pageSize).toString());
    queryParams.set('sort', 'title');
    queryParams.set('direction', 'asc');
    
    return apiGet<ArtistSongsResponse>(
      `songs/by-artist/${encodeURIComponent(artistName)}?${queryParams.toString()}`
    );
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['artist-songs', 'infinite', artistName, { pageSize }],
    queryFn: fetchSongsByArtist,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    enabled: !!artistName && (options.enabled !== false),
    staleTime: 2 * 60 * 1000, // 2 minutes
    initialPageParam: 0,
  });

  const songs = useMemo(() => {
    return data?.pages.flatMap(page => page?.songs ?? []).filter(Boolean) ?? [];
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
