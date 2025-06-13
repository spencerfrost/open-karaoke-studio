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
  searchThumbnailUrl?: string;  // Add field for original search thumbnail
}

export interface YouTubeDownloadResponse {
  tempId: string;
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
}

export interface MetadataOption {
  id: string;
  source: string;
  title: string;
  artist: string;
  album?: string;
  year?: string;
  duration?: string;
  genre?: string;
  language?: string;
  coverArtUrl?: string;
  musicbrainzId?: string;
}

export interface SaveMetadataRequest {
  title: string;
  artist: string;
  album?: string;
  lyrics?: string;
  syncedLyrics?: string;
  musicbrainzId?: string;
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
 * Hook to search for metadata using MusicBrainz
 */
export const useMetadataSearch = (
  params: MetadataSearchRequest,
  options?: UseQueryOptions<MetadataOption[], Error>
) => {
  const queryKey = ['metadata', 'search', params];
  const queryString = new URLSearchParams({
    title: params.title,
    artist: params.artist
  }).toString();
  
  return useApiQuery(
    queryKey,
    `musicbrainz/search?${queryString}`,
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
    `songs/${songId}`,
    'patch',
    options
  );
};