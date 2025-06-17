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

// Types
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

interface SongSearchResponse {
  songs: Song[];
  pagination: PaginationInfo;
}

interface ArtistSearchResponse {
  artists: Artist[];
  pagination: PaginationInfo;
}

export interface FuzzySearchResult {
  songs: Song[];
  artists: Artist[];
  songsPagination: {
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    fetchNextPage: () => void;
  };
  artistsPagination: {
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    fetchNextPage: () => void;
  };
  isLoading: boolean;
  error: Error | null;
}

/**
 * Hook for fuzzy search with dual display - searches both songs and artists
 *
 * Makes two parallel infinite queries:
 * 1. Song search (flat results)
 * 2. Artist search (for artist browsing)
 *
 * @param searchTerm - Search query
 * @param songPageSize - Number of songs to fetch per page (default: 20)
 * @param artistPageSize - Number of artists to fetch per page (default: 200)
 */
export const useInfiniteFuzzySearch = (
  searchTerm: string,
  songPageSize: number = 20,
  artistPageSize: number = 200
): FuzzySearchResult => {

  // Song search query (flat results)
  const fetchSongs = async ({ pageParam = 0 }) => {
    if (!searchTerm.trim()) {
      return { songs: [], pagination: { total: 0, limit: 0, offset: 0, hasMore: false } };
    }

    const queryParams = new URLSearchParams();
    queryParams.set('q', searchTerm);
    queryParams.set('group_by_artist', 'false'); // Flat song results
    queryParams.set('limit', songPageSize.toString());
    queryParams.set('offset', (pageParam * songPageSize).toString());
    queryParams.set('sort', 'relevance');
    queryParams.set('direction', 'desc');

    const url = `songs/search?${queryParams.toString()}`;
    return apiGet<SongSearchResponse>(url);
  };

  const songsQuery = useInfiniteQuery({
    queryKey: ['fuzzy-search', 'songs', { search: searchTerm, pageSize: songPageSize }],
    queryFn: fetchSongs,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    enabled: !!searchTerm.trim(),
    staleTime: 2 * 60 * 1000, // 2 minutes
    initialPageParam: 0,
  });

  // Artist search query (for artist browsing fallback)
  const fetchArtists = async ({ pageParam = 0 }) => {
    const queryParams = new URLSearchParams();
    if (searchTerm.trim()) {
      queryParams.set('search', searchTerm);
    }
    queryParams.set('limit', artistPageSize.toString());
    queryParams.set('offset', (pageParam * artistPageSize).toString());

    return apiGet<ArtistSearchResponse>(`songs/artists?${queryParams.toString()}`);
  };

  const artistsQuery = useInfiniteQuery({
    queryKey: ['fuzzy-search', 'artists', { search: searchTerm, pageSize: artistPageSize }],
    queryFn: fetchArtists,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    initialPageParam: 0,
  });

  // Flatten results
  const songs = useMemo(() => {
    return songsQuery.data?.pages.flatMap(page => page?.songs ?? []).filter(Boolean) ?? [];
  }, [songsQuery.data]);

  const artists = useMemo(() => {
    return artistsQuery.data?.pages.flatMap(page => page?.artists ?? []).filter(Boolean) ?? [];
  }, [artistsQuery.data]);

  // Combined loading state
  const isLoading = songsQuery.isLoading || artistsQuery.isLoading;

  // Combined error state (prioritize song search errors)
  const error = songsQuery.error || artistsQuery.error;

  return {
    songs,
    artists,
    songsPagination: {
      hasNextPage: songsQuery.hasNextPage ?? false,
      isFetchingNextPage: songsQuery.isFetchingNextPage,
      fetchNextPage: songsQuery.fetchNextPage,
    },
    artistsPagination: {
      hasNextPage: artistsQuery.hasNextPage ?? false,
      isFetchingNextPage: artistsQuery.isFetchingNextPage,
      fetchNextPage: artistsQuery.fetchNextPage,
    },
    isLoading,
    error: error as Error | null,
  };
};
