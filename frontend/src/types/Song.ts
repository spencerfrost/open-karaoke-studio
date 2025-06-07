export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface Song {
  id: string;
  title: string;
  artist: string;
  duration: number; // in seconds
  status: SongStatus;
  uploader: string;
  uploadId: string;
  channel: string;
  channelId: string;
  favorite: boolean;
  dateAdded: string;
  coverArt?: string;
  thumbnail?: string;
  vocalPath?: string;
  instrumentalPath?: string;
  originalPath?: string;
  // Additional metadata fields
  album?: string;
  year?: string;
  genre?: string;
  language?: string;
  metadataId?: string; // Used by backend for metadata lookup (iTunes ID, etc.)
  // Lyrics fields
  lyrics?: string; // Plain text lyrics
  syncedLyrics?: string; // LRC format synchronized lyrics
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
