// frontend/src/hooks/useYoutube.ts
import { useApiMutation, useApiQuery } from './useApi';
import { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';

// --- Types ---
export interface YouTubeDownloadRequest {
  videoId: string;
  artist?: string;
  title?: string;
  album?: string;
  songId?: string;
}

export interface YouTubeDownloadResponse {
  jobId: string;  // Changed from tempId to jobId to match new backend response
  status: string;
  message: string;
}

export interface LyricsSearchRequest {
  title: string;
  artist: string;
  album?: string;
}

export interface MetadataSearchRequest {
  title: string;
  artist: string;
}

export interface CreateSongRequest {
  title: string;
  artist: string;
  album?: string;
  source?: string;
  sourceUrl?: string;
  videoId?: string;
  videoTitle?: string;
}

export interface CreateSongResponse {
  id: string;
  title: string;
  artist: string;
  album?: string;
  dateAdded?: string;
  status: string;
}

export interface LyricsOption {
  id: string;
  source: string;
  trackName?: string;
  artistName?: string;
  plainLyrics?: string;
  syncedLyrics?: string;
  preview?: string;
  duration?: number;
  albumName?: string;
  name?: string;
  instrumental?: boolean;
}

export interface MetadataOption {
  metadataId: string;
  title: string;
  artist: string;
  artistId: number;
  album?: string;
  albumId?: number;
  releaseYear?: number;
  releaseDate?: string;
  duration?: number;
  discNumber?: number;
  trackNumber?: number;
  genre?: string;
  country?: string;
  artworkUrl?: string;
  previewUrl?: string;
  explicit?: boolean;
  isStreamable?: boolean;
  price?: number;
}

export interface MetadataSearchResponse {
  count: number;
  results: MetadataOption[];
  search: {
    album: string;
    artist: string;
    limit: number;
    sort_by: string;
    title: string;
  };
  success: boolean;
}

export interface SaveMetadataRequest {
  title: string;
  artist: string;
  album?: string;
  lyrics?: string;
  syncedLyrics?: string;
  metadataId?: string;
}

export interface SaveMetadataResponse {
  success: boolean;
  message: string;
}

// --- Mutations ---

/**
 * Hook to download a YouTube video and queue it for processing.
 * This hook immediately triggers the download on the server.
 */
export const useYoutubeDownloadMutation = (
  options?: UseMutationOptions<YouTubeDownloadResponse, Error, YouTubeDownloadRequest>
) => {
  return useApiMutation<YouTubeDownloadResponse, YouTubeDownloadRequest>(
    'youtube/download',
    'post',
    options
  );
};
/**
 * Hook to search for lyrics using the lyrics API
 */
export const useLyricsSearch = (
  params: LyricsSearchRequest,
  options?: UseQueryOptions<LyricsOption[], Error>
) => {
  const queryKey = ['lyrics', 'search', params];
  const queryString = new URLSearchParams({
    track_name: params.title,
    artist_name: params.artist,
    ...(params.album ? { album_name: params.album } : {})
  }).toString();
  
  return useApiQuery(
    queryKey,
    `lyrics/search?${queryString}`,
    options
  );
};

/**
 * Hook to search for metadata using Metadata API
 */
export const useMetadataSearch = (
  params: MetadataSearchRequest,
  options?: UseQueryOptions<MetadataSearchResponse, Error>
) => {
  const queryKey = ['metadata', 'search', params];
  const queryString = new URLSearchParams({
    title: params.title,
    artist: params.artist
  }).toString();
  
  return useApiQuery(
    queryKey,
    `metadata/search?${queryString}`,
    options
  );
};

/**
 * Hook to create a new song with basic metadata in the database
 */
export const useCreateSongMutation = (
  options?: UseMutationOptions<CreateSongResponse, Error, CreateSongRequest>
) => {
  return useApiMutation<CreateSongResponse, CreateSongRequest>(
    'songs',
    'post',
    options
  );
};


/**
 * Hook to save the final metadata and lyrics selection to the song
 */
export const useSaveMetadataMutation = (
  songId: string,
  options?: UseMutationOptions<SaveMetadataResponse, Error, SaveMetadataRequest>
) => {
  return useApiMutation<SaveMetadataResponse, SaveMetadataRequest>(
    `songs/${songId}/metadata`,
    'patch',
    options
  );
};