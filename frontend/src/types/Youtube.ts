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
  artistId?: string;
  duration: string; // ISO or mm:ss as returned by backend
  album?: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
  existsInLibrary: boolean;
  trackNumber?: number;
  isExplicit?: boolean;
}

export interface YoutubeMusicArtistSearchResult {
  browseId: string;
  name: string;
  subscribers?: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
}

export interface YoutubeMusicSearchResponse {
  artists: YoutubeMusicArtistSearchResult[];
  songs: YoutubeMusicSearchResult[];
  error: string | null;
}

// Artist browse types
export interface YoutubeMusicArtist {
  id: string;
  name: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
  description?: string;
  subscribers?: string;
}

export interface YoutubeMusicAlbum {
  browseId: string;
  title: string;
  year?: string;
  type: "album" | "single";
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
}

export interface YoutubeMusicArtistResponse {
  artist: YoutubeMusicArtist;
  topSongs: YoutubeMusicSearchResult[];
  albums: YoutubeMusicAlbum[];
}

export interface YoutubeMusicAlbumInfo {
  browseId: string;
  title: string;
  artist?: string;
  year?: string;
  thumbnails: Array<{ url: string; width?: number; height?: number }>;
  trackCount: number;
}

export interface YoutubeMusicAlbumTracksResponse {
  album: YoutubeMusicAlbumInfo;
  tracks: YoutubeMusicSearchResult[];
}
