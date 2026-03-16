export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface ChordEvent {
  time: number;
  chord: string;
}

export interface Song {
  id: string;
  title: string;
  artist: string;
  duration?: number; // Duration in seconds
  dateAdded?: string;

  backingVocalPath?: string;
  coverArt?: string;
  thumbnail?: string;

  // Source
  source?: string;
  sourceUrl?: string;
  videoId?: string;

  // Metadata
  album?: string;
  releaseDate?: string;
  year?: number;
  genre?: string;

  // Lyrics
  plainLyrics?: string;
  syncedLyrics?: string;

  // iTunes metadata
  itunesTrackId?: number;
  itunesExplicit?: boolean;
  itunesPreviewUrl?: string; // 30-sec preview for "what's this song again?"
  itunesArtworkUrls?: string; // JSON string from backend

  // YouTube thumbnail URLs (fallback for artwork)
  youtubeThumbnailUrls?: string; // JSON string from backend

  // Processing metadata
  engineType?: string; // Separation engine used (demucs, roformer, hybrid, clean_backing)

  // Audio analysis
  bpm?: number; // Beats per minute for count-in timing
  chordsData?: ChordEvent[];
  vocalRangeLow?: string; // Lowest note detected, e.g. "G2"
  vocalRangeHigh?: string; // Highest note detected, e.g. "E5"

  // Loudness normalization
  loudnessDbfs?: number; // RMS loudness in dBFS (e.g. -20.0)
  gainDb?: number; // Gain correction to reach -14 dBFS target

  status: SongStatus;
}

export interface SongProcessingRequest {
  file: File;
  title?: string;
  artist?: string;
}

export interface SongProcessingStatus {
  id: string;
  song_id?: string; // Links to the songs table
  progress: number; // 0-100
  status: SongStatus;
  message?: string;
  artist?: string;
  title?: string;
}

export interface LyricsResult {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  source: string;
}
