import { useQuery } from "@tanstack/react-query";
import { YoutubeVideoSearchResult } from "@/components/add/youtube-video/types";

interface UseYoutubeVideoSearchParams {
  query: string;
  enabled?: boolean;
}

interface YoutubeVideoSearchResponse {
  data: YoutubeVideoSearchResult[];
  error?: string;
}

/**
 * Hook for searching YouTube videos with a simple query string
 * This replaces the manual fetch logic in the original YoutubeVideoSearch component
 */
export const useYoutubeVideoSearch = ({
  query,
  enabled = true,
}: UseYoutubeVideoSearchParams) => {
  return useQuery({
    queryKey: ["youtube-search", query],
    queryFn: async (): Promise<YoutubeVideoSearchResult[]> => {
      if (!query.trim()) {
        return [];
      }

      const response = await fetch(
        `/api/youtube/search?query=${encodeURIComponent(query)}`,
      );

      const data: YoutubeVideoSearchResponse = await response.json();

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
