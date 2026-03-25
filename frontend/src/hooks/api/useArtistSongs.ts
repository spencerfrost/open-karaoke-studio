import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Song } from "../../types/Song";

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

interface PaginationInfo {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

interface ArtistSongsResponse {
  songs: Song[];
  artist: string;
  pagination: PaginationInfo;
}

interface InfiniteArtistSongsResult {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isLoading: boolean;
  error: Error | null;
}

export const useInfiniteArtistSongs = (
  artistName: string,
  pageSize: number = 10,
  options: { enabled?: boolean } = {},
): InfiniteArtistSongsResult => {
  const fetchSongsByArtist = async ({ pageParam = 0 }) => {
    const queryParams = new URLSearchParams();
    queryParams.set("limit", pageSize.toString());
    queryParams.set("offset", (pageParam * pageSize).toString());
    queryParams.set("sort", "title");
    queryParams.set("direction", "asc");

    return apiGet<ArtistSongsResponse>(
      `songs/by-artist/${encodeURIComponent(artistName)}?${queryParams.toString()}`,
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
    queryKey: ["artist-songs", "infinite", artistName, { pageSize }],
    queryFn: fetchSongsByArtist,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    enabled: !!artistName && options.enabled !== false,
    staleTime: 2 * 60 * 1000, // 2 minutes
    initialPageParam: 0,
  });

  const songs = useMemo(() => {
    return (
      data?.pages.flatMap((page) => page?.songs ?? []).filter(Boolean) ?? []
    );
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
