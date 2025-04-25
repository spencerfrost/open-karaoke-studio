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

export interface MetadataResponse {
  title: string;
  artist: string;
}

export interface LyricsResponse {
  lyrics?: string;
  syncedLyrics?: string;
  success: boolean;
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
 * Download a YouTube video as MP3 with optional metadata
 */
export async function downloadYouTubeVideo(
  videoId: string,
  metadata?: { title?: string; artist?: string }
) {
  return apiRequest<YouTubeDownloadResponse>("/api/youtube/download", {
    method: "POST",
    body: {
      video_id: videoId,
      ...metadata,
    },
  });
}

/**
 * Fetch parsed metadata for a YouTube video
 */
export async function fetchParsedMetadata(videoId: string) {
  const response = await apiRequest<MetadataResponse>("/api/youtube/parse-metadata", {
    method: "POST",
    body: {
      video_id: videoId,
    },
  });
  
  if (response.error) {
    throw new Error(response.error);
  }
  
  return response.data as MetadataResponse;
}

/**
 * Fetch enhanced metadata from MusicBrainz for a song
 */
export async function fetchEnhancedMetadata(title: string, artist: string, songId?: string) {
  return apiRequest<any>("/api/musicbrainz/search", {
    method: "POST",
    body: {
      title,
      artist,
      song_id: songId,
    },
  });
}

/**
 * Fetch lyrics from LRCLIB for a song
 */
export async function fetchLyrics(title: string, artist: string, songId?: string) {
  return apiRequest<LyricsResponse>("/api/lyrics/search", {
    method: "POST",
    body: {
      title,
      artist,
      song_id: songId,
    },
  });
}
