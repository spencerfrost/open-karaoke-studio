export type SongStatus = "processing" | "queued" | "processed" | "error";

// class DbSong(Base):
//     __tablename__ = "songs"
//     id = Column(String, primary_key=True)
//     title = Column(String, nullable=False)
//     artist = Column(String, nullable=False, default=UNKNOWN_ARTIST)
//     duration_ms = Column(Integer, nullable=True)
//     date_added = Column(DateTime, default=datetime.now(timezone.utc))
//     vocals_path = Column(String, nullable=True)
//     instrumental_path = Column(String, nullable=True)
//     original_path = Column(String, nullable=True)
//     thumbnail_path = Column(String, nullable=True)
//     cover_art_path = Column(String, nullable=True)
//     source = Column(String, nullable=True)
//     source_url = Column(String, nullable=True)
//     video_id = Column(String, nullable=True)
//     uploader = Column(String, nullable=True)
//     uploader_id = Column(String, nullable=True)
//     channel = Column(String, nullable=True)
//     channel_id = Column(String, nullable=True)
//     description = Column(Text, nullable=True)  # Song/video description

//     # Phase 1A = Column(Text, nullable=True)
//     upload_date = Column(DateTime, nullable=True)
//     mbid = Column(String, nullable=True)
//     album = Column(String, nullable=True)  # Renamed from release_title for better UX
//     release_id = Column(String, nullable=True)
//     release_date = Column(String, nullable=True)
//     year = Column(Integer, nullable=True)
//     genre = Column(String, nullable=True)
//     language = Column(String, nullable=True)
//     lyrics = Column(Text, nullable=True)
//     synced_lyrics = Column(Text, nullable=True)
//     channel_name = Column(String, nullable=True)  # Legacy field

//     # Phase 1B = Column(Integer, nullable=True)
//     itunes_artist_id = Column(Integer, nullable=True)
//     itunes_collection_id = Column(Integer, nullable=True)
//     track_time_millis = Column(Integer, nullable=True)
//     itunes_explicit = Column(Boolean, nullable=True)
//     itunes_preview_url = Column(String, nullable=True)
//     itunes_artwork_urls = Column(Text, nullable=True)  # JSON array as string

//     # Phase 1B = Column(Integer, nullable=True)
//     youtube_thumbnail_urls = Column(Text, nullable=True)  # JSON array as string
//     youtube_tags = Column(Text, nullable=True)  # JSON array as string
//     youtube_categories = Column(Text, nullable=True)  # JSON array as string
//     youtube_channel_id = Column(String, nullable=True)
//     youtube_channel_name = Column(String, nullable=True)

//     # Phase 1B = Column(Text, nullable=True)  # JSON string
//     youtube_raw_metadata = Column(Text, nullable=True)  # JSON string
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
  youtubeRawMetadata?: any;

  // Metadata
  mbid?: string;
  album?: string;
  releaseId?: string;
  releaseDate?: string;
  year?: number;
  genre?: string;
  language?: string;

  // Lyrics
  lyrics?: string;
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
