import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Song, SongArtist } from "../../types/Song";
import { apiGet } from "./useApi";

interface PaginationInfo {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

/** A song in an artist's list, with the artist's role on it. */
export type ArtistSong = Song & { role?: SongArtist["role"] };

interface ArtistSongsResponse {
  /** Their own songs first, then the ones they're featured on. */
  songs: ArtistSong[];
  artist: { id: number; name: string; youtubeMusicArtistId: string | null };
  pagination: PaginationInfo;
}

interface InfiniteArtistSongsResult {
  songs: ArtistSong[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isLoading: boolean;
  error: Error | null;
}

export const useInfiniteArtistSongs = (
  artistId: number | null,
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
      `songs/by-artist/${artistId}?${queryParams.toString()}`,
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
    queryKey: ["artist-songs", "infinite", artistId, { pageSize }],
    queryFn: fetchSongsByArtist,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    enabled: artistId !== null && options.enabled !== false,
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

interface ShowSongsResponse {
  songs: Song[];
  show: string;
  pagination: PaginationInfo;
}

export const useInfiniteShowSongs = (
  showName: string,
  pageSize: number = 10,
  options: { enabled?: boolean } = {},
): InfiniteArtistSongsResult => {
  const fetchSongsByShow = async ({ pageParam = 0 }) => {
    const queryParams = new URLSearchParams();
    queryParams.set("limit", pageSize.toString());
    queryParams.set("offset", (pageParam * pageSize).toString());
    queryParams.set("sort", "title");
    queryParams.set("direction", "asc");

    return apiGet<ShowSongsResponse>(
      `songs/by-show/${encodeURIComponent(showName)}?${queryParams.toString()}`,
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
    queryKey: ["show-songs", "infinite", showName, { pageSize }],
    queryFn: fetchSongsByShow,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage?.pagination?.hasMore) return undefined;
      return allPages.length;
    },
    enabled: !!showName && options.enabled !== false,
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
