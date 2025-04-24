/**
 * YouTube-related API services
 */
import { apiRequest } from "./api";

export interface YouTubeSearchResult {
  id: string;
  title: string;
  uploader: string;
  duration: number;
  thumbnail: string;
  url: string;
}

export interface YouTubeSearchResponse {
  results: YouTubeSearchResult[];
}

export interface YouTubeDownloadResponse {
  success: boolean;
  file: string;
  metadata: {
    id: string;
    title: string;
    duration: number;
    uploader: string;
  };
}

/**
 * Search YouTube for videos matching the query
 */
export async function searchYouTube(query: string, maxResults: number = 10) {
  return apiRequest<YouTubeSearchResponse>("/api/youtube/search", {
    method: "POST",
    body: {
      query,
      max_results: maxResults,
    },
  });
}

/**
 * Download a YouTube video as MP3
 */
export async function downloadYouTubeVideo(videoId: string) {
  return apiRequest<YouTubeDownloadResponse>("/api/youtube/download", {
    method: "POST",
    body: {
      video_id: videoId,
    },
  });
}
