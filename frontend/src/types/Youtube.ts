// frontend/src/types/Youtube.ts

export interface Thumbnail {
  url: string;
  width?: number;
  height?: number;
}

/**
 * A song's copy in the library: ready to sing, still processing, or failed
 * (the only copy, so adding the song again restarts it).
 */
export interface LibraryEntry {
  status: "ready" | "processing" | "failed";
  songId: string;
}

export interface YoutubeVideoSearchResult {
  id: string;
  title: string;
  channel: string;
  duration: number;
  thumbnail: string;
  url: string;
  library: LibraryEntry | null;
}

export interface ArtistCredit {
  name: string;
  id?: string | null;
}

/** One song, the same shape in search, popular songs and album tracks. */
export interface YoutubeMusicSong {
  /** Missing when YouTube Music can't play the track. */
  videoId: string | null;
  title: string | null;
  artists: ArtistCredit[];
  /** The artists as the one credit line the library stores. */
  artist: string | null;
  album: string | null;
  albumId: string | null;
  durationSeconds: number | null;
  isExplicit: boolean;
  thumbnails: Thumbnail[];
  trackNumber?: number | null;
  library: LibraryEntry | null;
}

export interface YoutubeMusicArtistSearchResult {
  browseId: string;
  name: string;
  subscribers?: string | null;
  thumbnails: Thumbnail[];
}

/** Song results sorted by what a guest is looking for. */
export interface YoutubeMusicSearchResponse {
  bestMatch: YoutubeMusicSong | null;
  /** The best match's song by other artists, or live, acoustic, remixed... */
  otherVersions: YoutubeMusicSong[];
  otherSongs: YoutubeMusicSong[];
  artists: YoutubeMusicArtistSearchResult[];
  /** Set when YouTube Music's top result for the query is this artist. */
  topArtistId: string | null;
}

export interface YoutubeMusicArtist {
  id: string;
  name: string | null;
  thumbnails: Thumbnail[];
  description?: string | null;
  subscribers?: string | null;
}

export interface YoutubeMusicRelease {
  browseId: string | null;
  title: string | null;
  year?: string | null;
  type: string;
  thumbnails: Thumbnail[];
}

export interface YoutubeMusicArtistResponse {
  artist: YoutubeMusicArtist;
  topSongs: YoutubeMusicSong[];
  /** More popular songs than topSongs: the artist's songs endpoint has them all. */
  hasMoreSongs: boolean;
  /** Every album, oldest first. */
  albums: YoutubeMusicRelease[];
  /** Every single, oldest first. */
  singles: YoutubeMusicRelease[];
  /** Remixes from the albums and singles, oldest first. */
  remixes: YoutubeMusicRelease[];
}

export interface YoutubeMusicAlbumInfo {
  browseId: string;
  title: string | null;
  artists: ArtistCredit[];
  /** "Album", "Single", "EP" */
  type: string | null;
  year?: string | null;
  thumbnails: Thumbnail[];
  trackCount: number;
}

export interface YoutubeMusicAlbumResponse {
  album: YoutubeMusicAlbumInfo;
  tracks: YoutubeMusicSong[];
}
