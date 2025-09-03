import { useApiQuery } from "./api/useApi";
import { YoutubeVideoSearchResponse } from "@/types/Youtube";

interface UseYoutubeVideoSearchParams {
  query: string;
  enabled?: boolean;
}

/**
 * Hook for searching YouTube videos using the unified API pattern
 * Now consistent with useYoutubeMusicSearch and other API hooks
 */
export const useYoutubeVideoSearch = ({
  query,
  enabled = true,
}: UseYoutubeVideoSearchParams) => {
  const result = useApiQuery<
    YoutubeVideoSearchResponse,
    ["youtube-search", string]
  >(
    ["youtube-search", query],
    `youtube/search?query=${encodeURIComponent(query)}`,
    {
      enabled: enabled && !!query.trim(),
      staleTime: 5 * 60 * 1000, // Cache results for 5 minutes
      retry: 2,
    },
  );

  // Transform the result to match the expected interface
  return {
    ...result,
    data: result.data?.results || [],
  };
};
