/**
 * Song-related API services
 */
import { Song } from "../types/Song";
import {
  apiRequest,
  downloadFile,
  API_BASE as API_HOST,
  ApiResponse,
  HttpMethod,
} from "./api";

const API_PATH = "/api";

/**
 * Get a playback URL for a given song track type
 */
export function getAudioUrl(
  songId: string,
  trackType: "vocals" | "instrumental" | "original",
): string {
  return `${API_HOST}${API_PATH}/songs/${songId}/download/${trackType}`;
}

/**
 * Get all songs in the library
 */
export async function getSongs(): Promise<ApiResponse<Song[]>> {
  return apiRequest<Song[]>(`${API_PATH}/songs`);
}

/**
 * Get a specific song by ID
 */
export async function getSongById(id: string): Promise<ApiResponse<Song>> {
  return apiRequest<Song>(`${API_PATH}/songs/${id}`);
}

/**
 * Update a song
 */
export async function updateSong(
  id: string,
  updates: Partial<Song>,
): Promise<ApiResponse<Song>> {
  return apiRequest<Song>(`${API_PATH}/songs/${id}`, {
    method: "PUT",
    body: updates,
  });
}

/**
 * Delete a song
 */
export async function deleteSong(
  id: string,
): Promise<ApiResponse<{ success: boolean }>> {
  return apiRequest<{ success: boolean }>(`${API_PATH}/songs/${id}`, {
    method: "DELETE",
  });
}

/**
 * Toggle favorite status of a song
 */
export async function toggleFavorite(
  id: string,
  isFavorite: boolean,
): Promise<ApiResponse<Song>> {
  console.warn(
    "toggleFavorite endpoint not implemented in backend blueprint yet.",
  );
  return updateSong(id, { favorite: isFavorite });
}

/**
 * Download vocal track
 */
export async function downloadVocals(
  songId: string,
  filename?: string,
): Promise<void> {
  const url = `${API_PATH}/songs/${songId}/download/vocals`;
  return downloadFile(url, filename ?? `vocals-${songId}.mp3`);
}

/**
 * Download instrumental track
 */
export async function downloadInstrumental(
  songId: string,
  filename?: string,
): Promise<void> {
  const url = `${API_PATH}/songs/${songId}/download/instrumental`;
  return downloadFile(url, filename ?? `instrumental-${songId}.mp3`);
}

/**
 * Download original track
 */
export async function downloadOriginal(
  songId: string,
  filename?: string,
): Promise<void> {
  const url = `${API_PATH}/songs/${songId}/download/original`;
  return downloadFile(url, filename ?? `original-${songId}.mp3`);
}

/**
 * Update song metadata
 */
export async function updateSongMetadata(
  id: string,
  metadata: Partial<Song>,
): Promise<ApiResponse<Song>> {
  return apiRequest<Song>(`${API_PATH}/songs/${id}/metadata`, {
    method: "PATCH" as HttpMethod,
    body: metadata,
  });
}

/**
 * Search MusicBrainz for song metadata
 */
export async function searchMusicBrainz(query: {
  title?: string;
  artist?: string;
}): Promise<ApiResponse<Array<Partial<Song>>>> {
  return apiRequest<Array<Partial<Song>>>(`${API_PATH}/musicbrainz/search`, {
    method: "POST",
    body: query,
  });
}

/**
 * Get song processing status
 */
export async function getSongStatus(
  id: string,
): Promise<ApiResponse<{ status: string; progress?: number }>> {
  console.warn(
    "getSongStatus may require original filename, not song_id, for current /status endpoint",
  );
  return apiRequest<{ status: string; progress?: number }>(`/status/${id}`);
}

/**
 * Fetch lyrics for a specific song by ID
 */
export async function getSongLyrics(songId: string): Promise<
  ApiResponse<{
    plainLyrics: string;
    syncedLyrics: string;
    duration: number;
  }>
> {
  return apiRequest<{
    plainLyrics: string;
    syncedLyrics: string;
    duration: number;
  }>(`${API_PATH}/songs/${songId}/lyrics`);
}

/**
 * Search for lyrics using keywords
 */
export async function searchLyrics(query: {
  q?: string;
  track_name?: string;
  artist_name?: string;
  album_name?: string;
}): Promise<
  ApiResponse<
    Array<{
      id: number;
      trackName: string;
      artistName: string;
      albumName: string;
      duration: number;
      plainLyrics: string | null;
      syncedLyrics: string | null;
    }>
  >
> {
  const queryParams = new URLSearchParams(query as Record<string, string>);
  return apiRequest<
    Array<{
      id: number;
      trackName: string;
      artistName: string;
      albumName: string;
      duration: number;
      plainLyrics: string | null;
      syncedLyrics: string | null;
    }>
  >(`${API_PATH}/lyrics/search?${queryParams.toString()}`);
}
