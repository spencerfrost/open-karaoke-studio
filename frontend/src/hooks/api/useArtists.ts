import { useQuery } from '@tanstack/react-query';

export interface Artist {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface UseArtistsParams {
  search?: string;
  limit?: number;
  offset?: number;
}

interface UseArtistsResult {
  artists: Artist[];
  isLoading: boolean;
  error: unknown;
}

export function useArtists({ search = '', limit = 200, offset = 0 }: UseArtistsParams = {}): UseArtistsResult {
  const queryKey = ['artists', { search, limit, offset }];
  const queryFn = async () => {
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search);
    params.set('limit', limit.toString());
    params.set('offset', offset.toString());
    const res = await fetch(`/api/songs/artists?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch artists');
    const data = await res.json();
    return Array.isArray(data.artists) ? data.artists : [];
  };

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return {
    artists: data ?? [],
    isLoading,
    error,
  };
}
