export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface Song {
  // Core fields
  id: string;
  title: string;
  artist: string;
  album: string; // Primary field (was releaseTitle)
  duration_ms: number; // in milliseconds
  status: SongStatus;
  
  // Media files
  coverArt?: string;
  thumbnail?: string;
  vocalPath?: string;
  instrumentalPath?: string;
  originalPath?: string;
  
  // iTunes metadata
  itunesTrackId?: number;
  itunesArtistId?: number;
  itunesCollectionId?: number;
  trackTimeMillis?: number;
  itunesExplicit?: boolean;
  itunesPreviewUrl?: string;
  itunesArtworkUrls?: {
    60?: string;
    100?: string;
    600?: string;
  };
  
  // YouTube metadata (enhanced)
  videoId?: string;
  youtubeDuration?: number;
  youtubeThumbnailUrls?: {
    default?: string;
    medium?: string;
    high?: string;
    standard?: string;
    maxres?: string;
  };
  youtubeTags?: string[];
  youtubeCategories?: string[];
  youtubeChannelId?: string;
  youtubeChannelName?: string;
  
  // Existing fields (maintained for compatibility)
  uploader?: string;
  uploaderId?: string;
  channel?: string;
  channelId?: string;
  description?: string;
  uploadDate?: string;
  favorite: boolean;
  dateAdded: string;
  genre?: string;
  language?: string;
  lyrics?: string; // Plain text lyrics
  syncedLyrics?: string; // LRC format synchronized lyrics
  
  // Legacy/compatibility (for transition period)
  releaseTitle?: string; // Backwards compatibility, maps to album
  year?: string;
  uploadId?: string;
  metadataId?: string;
  
  // MusicBrainz metadata (maintained)
  mbid?: string;
  releaseId?: string;
  releaseDate?: string;
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
