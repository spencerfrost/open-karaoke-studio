import { useQuery } from "@tanstack/react-query";

export interface Artist {
  id: number;
  name: string;
  songCount: number;
  firstLetter: string;
}

interface UseArtistsParams {
  search?: string;
}

interface UseArtistsResult {
  artists: Artist[];
  isLoading: boolean;
  error: unknown;
}

export function useArtists({ search = "" }: UseArtistsParams = {}): UseArtistsResult {
  const queryKey = ["artists", { search }];
  const queryFn = async () => {
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search);
    const res = await fetch(`/api/songs/artists?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch artists");
    const data = await res.json();
    return Array.isArray(data.artists) ? data.artists : [];
  };

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    artists: data ?? [],
    isLoading,
    error,
  };
}
