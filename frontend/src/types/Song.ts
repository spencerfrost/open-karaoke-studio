export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface ChordEvent {
  time: number;
  chord: string;
}

export interface SongArtist {
  id: number;
  name: string;
  role: 'primary' | 'featured';
}

export interface Song {
  id: string;
  title: string;
  artist: string;
  artists?: SongArtist[];
  duration?: number; // Duration in seconds
  dateAdded?: string;

  backingVocalPath?: string;
  thumbnail?: string;

  // Source
  source?: string;
  sourceUrl?: string;
  videoId?: string;

  // Metadata
  album?: string;
  releaseDate?: string;
  year?: number;

  // Lyrics
  plainLyrics?: string;
  syncedLyrics?: string;
  wordSyncedLyrics?: string | null;

  // iTunes metadata
  itunesTrackId?: number;
  itunesExplicit?: boolean;
  itunesPreviewUrl?: string; // 30-sec preview for "what's this song again?"

  // Relational IDs and computed cover URL
  artistId?: number;
  albumId?: number;
  albumCoverUrl?: string; // Computed by backend — points to /api/albums/{id}/cover

  // AcoustID fingerprinting
  acoustidFingerprintStatus?: "not_checked" | "matched" | "no_match" | "failed";
  acoustidScore?: number;
  musicbrainzRecordingId?: string;

  // Processing metadata
  engineType?: string; // Separation engine used (demucs, roformer, hybrid, clean_backing)

  // Audio analysis
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
