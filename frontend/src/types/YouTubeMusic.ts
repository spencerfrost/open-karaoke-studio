// frontend/src/types/YouTubeMusic.ts

export interface YouTubeMusicSong {
  videoId: string;
  title: string;
  artist: string;
  duration: string; // ISO or mm:ss as returned by backend
  album?: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
}

export interface YouTubeMusicSearchResponse {
  results: YouTubeMusicSong[];
  error: string | null;
}
