export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface Song {
  id: string;
  title: string;
  artist: string;
  durationMs?: number;
  dateAdded?: string;

  // File paths (API URLs)
  vocalPath?: string;
  instrumentalPath?: string;
  originalPath?: string;
  coverArt?: string;
  thumbnail?: string;

  // Source
  source?: string;
  sourceUrl?: string;
  videoId?: string;

  // YouTube data
  uploader?: string;
  uploaderId?: string;
  channel?: string;
  channelId?: string;
  channelName?: string;
  description?: string;
  uploadDate?: string;
  youtubeThumbnailUrls?: string[];
  youtubeTags?: string[];
  youtubeCategories?: string[];
  youtubeChannelId?: string;
  youtubeChannelName?: string;
  youtubeRawMetadata?: Record<string, unknown>;

  // Metadata
  mbid?: string;
  album?: string;
  releaseId?: string;
  releaseDate?: string;
  year?: number;
  genre?: string;
  language?: string;

  // Lyrics
  plainLyrics?: string;
  syncedLyrics?: string;

  // iTunes data
  itunesArtistId?: number;
  itunesCollectionId?: number;
  trackTimeMillis?: number;
  itunesExplicit?: boolean;
  itunesPreviewUrl?: string;
  itunesArtworkUrls?: string[];

  status: SongStatus;
}

export interface SongProcessingRequest {
  file: File;
  title?: string;
  artist?: string;
}

export interface SongProcessingStatus {
  id: string;
  progress: number; // 0-100
  status: SongStatus;
  message?: string;
  artist?: string;
  title?: string;
}
