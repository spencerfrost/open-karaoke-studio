// frontend/src/types/Youtube.ts

export interface YoutubeVideoSearchResult {
  id: string;
  title: string;
  channel: string;
  duration: number;
  thumbnail: string;
  url: string;
}

export interface YoutubeVideoSearchResponse {
  results: YoutubeVideoSearchResult[];
  error: string | null;
}
export interface YoutubeMusicSearchResult {
  videoId: string;
  title: string;
  artist: string;
  duration: string; // ISO or mm:ss as returned by backend
  album?: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
}

export interface YoutubeMusicSearchResponse {
  results: YoutubeMusicSearchResult[];
  error: string | null;
}
