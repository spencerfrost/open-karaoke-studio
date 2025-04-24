/**
 * Song-related API services
 */
import { apiRequest, downloadFile, API_BASE as API_HOST } from "./api";
const API_PATH = "/api";
import { Song } from "../types/Song";

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
export async function getSongs() {
  return apiRequest<Song[]>(`${API_PATH}/songs`);
}

/**
 * Get a specific song by ID
 */
export async function getSongById(id: string) {
  return apiRequest<Song>(`${API_PATH}/songs/${id}`);
}

/**
 * Update a song
 */
export async function updateSong(id: string, updates: Partial<Song>) {
  return apiRequest<Song>(`${API_PATH}/songs/${id}`, {
    method: "PUT",
    body: updates,
  });
}

/**
 * Delete a song
 */
export async function deleteSong(id: string) {
  return apiRequest<{ success: boolean }>(`${API_PATH}/songs/${id}`, {
    method: "DELETE",
  });
}

/**
 * Toggle favorite status of a song
 */
export async function toggleFavorite(id: string, isFavorite: boolean) {
  console.warn(
    "toggleFavorite endpoint not implemented in backend blueprint yet.",
  );
  return updateSong(id, { favorite: isFavorite });
}

/**
 * Download vocal track
 */
export async function downloadVocals(songId: string, filename?: string) {
  const url = `${API_PATH}/songs/${songId}/download/vocals`;
  return downloadFile(url, filename || `vocals-${songId}.mp3`);
}

/**
 * Download instrumental track
 */
export async function downloadInstrumental(songId: string, filename?: string) {
  const url = `${API_PATH}/songs/${songId}/download/instrumental`;
  return downloadFile(url, filename || `instrumental-${songId}.mp3`);
}

/**
 * Download original track
 */
export async function downloadOriginal(songId: string, filename?: string) {
  const url = `${API_PATH}/songs/${songId}/download/original`;
  return downloadFile(url, filename || `original-${songId}.mp3`);
}

/**
 * Update song metadata
 */
export async function updateSongMetadata(id: string, metadata: Partial<Song>) {
  return apiRequest<Song>(`${API_PATH}/songs/${id}/metadata`, {
    method: "PATCH",
    body: metadata,
  });
}

/**
 * Search MusicBrainz for song metadata
 */
export async function searchMusicBrainz(query: {
  title?: string;
  artist?: string;
}) {
  return apiRequest<Array<Partial<Song>>>(`${API_PATH}/musicbrainz/search`, {
    method: "POST",
    body: query,
  });
}

/**
 * Get song processing status
 */
export async function getSongStatus(id: string) {
  console.warn(
    "getSongStatus may require original filename, not song_id, for current /status endpoint",
  );
  return apiRequest<{ status: string; progress?: number }>(`/status/${id}`);
}
