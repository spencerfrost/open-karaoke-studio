// frontend/src/hooks/useYouTubeMusic.ts
import { useApiQuery } from "./useApi";
import { YouTubeMusicSearchResponse } from "../../types/YouTubeMusic";

export function useYouTubeMusicSearch(query: string, enabled: boolean = true) {
  return useApiQuery<
    YouTubeMusicSearchResponse,
    ["youtube-music-search", string]
  >(
    ["youtube-music-search", query],
    `youtube-music/search?q=${encodeURIComponent(query)}`,
    {
      enabled: enabled && !!query,
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    }
  );
}
