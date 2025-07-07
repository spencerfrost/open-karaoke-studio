export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface Song {
  id: string;
  title: string;
  artist: string;
  durationMs?: number;
  favorite: boolean;
  dateAdded?: string;

  // File paths (API URLs)
  vocalPath?: string;
  instrumentalPath?: string;
  originalPath?: string;
  coverArt?: string;
  thumbnail?: string;

  // YouTube data
  videoId?: string;
  sourceUrl?: string;
  uploader?: string;
  uploaderId?: string;
  channel?: string;
  channelId?: string;
  channelName?: string;
  description?: string;
  uploadDate?: string;

  // Metadata
  mbid?: string;
  metadataId?: string;
  album?: string;
  releaseTitle?: string;
  releaseId?: string;
  releaseDate?: string;
  year?: number;
  genre?: string;
  language?: string;

  // Lyrics
  lyrics?: string;
  syncedLyrics?: string;

  // System
  source?: string;
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
