export type SongStatus = "processing" | "queued" | "processed" | "error";

export interface SongArtist {
  id: number;
  name: string;
  role: "primary" | "featured";
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
  showName?: string; // Musical/soundtrack, e.g. "Wicked"
  language?: string | null; // Sung language as a Whisper code ("fr"); null until detected
  lyricsHandPicked?: boolean; // A person saved the lyrics; automatic runs only time them

  // Lyrics
  plainLyrics?: string;
  syncedLyrics?: string;
  wordSyncedLyrics?: string | null;

  explicit?: boolean | null; // From the album lookup; null when it couldn't tell
  albumHandSet?: boolean; // A person set the album name; automatic lookups skip it

  // Relational IDs and computed cover URL
  artistId?: number;
  albumId?: number;
  albumCoverUrl?: string; // Computed by backend — points to /api/albums/{id}/cover

  // AcoustID fingerprinting
  acoustidFingerprintStatus?:
    | "not_checked"
    | "matched"
    | "suggested"
    | "no_match"
    | "ambiguous"
    | "skipped"
    | "failed";
  acoustidScore?: number;
  musicbrainzRecordingId?: string;
  // What AcoustID thinks the song is called, when that differs (status "suggested")
  acoustidSuggestion?: {
    recordingId: string;
    title: string | null;
    artist: string | null;
  } | null;
  metadataConfirmed?: boolean; // A person set the title/artist; AcoustID leaves them alone

  // Processing metadata
  engineType?: string; // Separation engine used (demucs, roformer, hybrid, clean_backing)

  // Audio analysis
  vocalRangeLow?: string; // Lowest note detected, e.g. "G2"
  vocalRangeHigh?: string; // Highest note detected, e.g. "E5"

  // Loudness normalization
  // Measured on the stems as played by default (no lead vocal)
  loudnessLufs?: number; // EBU R128 integrated loudness, e.g. -9.8
  truePeakDbtp?: number; // Loudest instant in dB true peak, e.g. -0.3
  gainDb?: number; // Correction the player applies, e.g. -6.2

  status: SongStatus;
  errorMessage?: string; // Failure reason when status="error"
  failedAt?: string | null; // When it last failed (UTC, no zone marker)
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
  rawStatus?: string; // Backend job status before mapping to SongStatus
  message?: string;
  artist?: string;
  title?: string;
  engineType?: string; // Separation engine running the job (demucs, lyrics_alignment, ...)
  engine_type?: string; // Snake-case variant as delivered by some websocket payloads
  /** The pipeline step this job is on, or waiting for while queued. */
  step?: JobStep | null;
  /** Which session added it. Compare with the session's own `owner_tag`. */
  ownerTag?: string | null;
  createdAt?: string;
}

/**
 * A song's pipeline, in order. Lyrics alignment runs as a separate job, so a
 * song's timeline can span two jobs.
 */
export const JOB_STEPS = ["download", "separate", "align"] as const;
export type JobStep = (typeof JOB_STEPS)[number];

export interface LyricsResult {
  id: string;
  title: string;
  artist: string;
  lyrics: string;
  source: string;
}
