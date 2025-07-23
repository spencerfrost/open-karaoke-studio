// frontend/src/hooks/useYoutube.ts
import { useApiMutation } from "./useApi";
import { UseMutationOptions } from "@tanstack/react-query";

// --- Types ---
export interface YouTubeDownloadRequest {
  video_id: string;
  artist?: string;
  title?: string;
  album?: string;
  song_id?: string;
  searchThumbnailUrl?: string; // Add field for original search thumbnail
}

export interface YouTubeDownloadResponse {
  jobId: string; // Changed from tempId to jobId to match new backend response
  status: string;
  message: string;
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

export interface SaveMetadataRequest {
  title: string;
  artist: string;
  album?: string;
  plainlyrics?: string;
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
  options?: UseMutationOptions<
    YouTubeDownloadResponse,
    Error,
    YouTubeDownloadRequest
  >
) => {
  return useApiMutation<YouTubeDownloadResponse, YouTubeDownloadRequest>(
    "youtube/download",
    "post",
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
    "songs",
    "post",
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
    "patch",
    options
  );
};
