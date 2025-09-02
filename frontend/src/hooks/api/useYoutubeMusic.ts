// frontend/src/hooks/useYoutubeMusic.ts
import { useApiQuery } from "./useApi";
import { YoutubeMusicSearchResponse } from "../../types/Youtube";

export function useYoutubeMusicSearch(query: string, enabled: boolean = true) {
  return useApiQuery<
    YoutubeMusicSearchResponse,
    ["youtube-music-search", string]
  >(
    ["youtube-music-search", query],
    `youtube-music/search?q=${encodeURIComponent(query)}`,
    {
      enabled: enabled && !!query,
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  );
}
