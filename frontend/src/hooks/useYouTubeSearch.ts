import { useQuery } from "@tanstack/react-query";
import { YouTubeSearchResult } from "@/components/add/youtube/YouTubeSearch";

interface UseYouTubeSearchParams {
  query: string;
  enabled?: boolean;
}

interface YouTubeSearchResponse {
  data: YouTubeSearchResult[];
  error?: string;
}

/**
 * Hook for searching YouTube videos with a simple query string
 * This replaces the manual fetch logic in the original YouTubeSearch component
 */
export const useYouTubeSearch = ({
  query,
  enabled = true,
}: UseYouTubeSearchParams) => {
  return useQuery({
    queryKey: ["youtube-search", query],
    queryFn: async (): Promise<YouTubeSearchResult[]> => {
      if (!query.trim()) {
        return [];
      }

      const response = await fetch(
        `/api/youtube/search?query=${encodeURIComponent(query)}`,
      );

      const data: YouTubeSearchResponse = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      return data.data || [];
    },
    enabled: enabled && !!query.trim(),
    staleTime: 5 * 60 * 1000, // Cache results for 5 minutes
    retry: 2,
  });
};
