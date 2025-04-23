/**
 * Song-related API services
 */
import { apiRequest, downloadFile } from "./api";
import { Song } from "../types/Song";

const API_BASE = "/api";

/**
 * Get all songs in the library
 */
export async function getSongs() {
  return apiRequest<Song[]>(`${API_BASE}/songs`);
}

/**
 * Get a specific song by ID
 */
export async function getSongById(id: string) {
  // Endpoint not yet implemented on backend blueprint
  return apiRequest<Song>(`${API_BASE}/songs/${id}`);
}

/**
 * Update a song
 */
export async function updateSong(id: string, updates: Partial<Song>) {
  // Endpoint not yet implemented on backend blueprint
  return apiRequest<Song>(`${API_BASE}/songs/${id}`, {
    method: "PUT", // Or PATCH
    body: updates,
  });
}

/**
 * Delete a song
 */
export async function deleteSong(id: string) {
  // Endpoint not yet implemented on backend blueprint
  return apiRequest<{ success: boolean }>(`${API_BASE}/songs/${id}`, {
    method: "DELETE",
  });
}

/**
 * Toggle favorite status of a song
 */
export async function toggleFavorite(id: string, isFavorite: boolean) {
  // Endpoint not yet implemented on backend blueprint - Requires PUT/PATCH on /api/songs/{id}
  // Example using PUT on a dedicated endpoint (if you prefer)
  // return apiRequest<Song>(`${API_BASE}/songs/${id}/favorite`, {
  //   method: 'PUT',
  //   body: { favorite: isFavorite },
  // });
  // For now, let's assume it's part of updateSong via PATCH/PUT
  console.warn(
    "toggleFavorite endpoint not implemented in backend blueprint yet."
  );
  return updateSong(id, { favorite: isFavorite }); // Simulate via updateSong
}

/**
 * Download vocal track
 */
export async function downloadVocals(songId: string, filename?: string) {
  // Filename might be optional now
  // Use the new RESTful download endpoint
  const url = `${API_BASE}/songs/${songId}/download/vocals`;
  // Pass filename if downloadFile utility uses it, otherwise backend determines it
  return downloadFile(url, filename || `vocals-${songId}.mp3`);
}

/**
 * Download instrumental track
 */
export async function downloadInstrumental(songId: string, filename?: string) {
  // Use the new RESTful download endpoint
  const url = `${API_BASE}/songs/${songId}/download/instrumental`;
  return downloadFile(url, filename || `instrumental-${songId}.mp3`);
}

/**
 * Download original track
 */
export async function downloadOriginal(songId: string, filename?: string) {
  // Use the new RESTful download endpoint
  const url = `${API_BASE}/songs/${songId}/download/original`;
  return downloadFile(url, filename || `original-${songId}.mp3`); // Default filename might be inaccurate
}

/**
 * Update song metadata
 */
export async function updateSongMetadata(id: string, metadata: Partial<Song>) {
  return apiRequest<Song>(`${API_BASE}/songs/${id}/metadata`, {
    method: "PATCH",
    body: metadata,
  });
}

/**
 * Search MusicBrainz for song metadata
 */
export async function searchMusicBrainz(query: { title?: string; artist?: string }) {
  return apiRequest<Array<Partial<Song>>>(`${API_BASE}/musicbrainz/search`, {
    method: "POST",
    body: query,
  });
}

/**
 * Get song processing status
 */
export async function getSongStatus(id: string) {
  // Uses the original /status endpoint (consider moving later)
  // Assuming id here might be the original filename, not song_id? Needs clarification.
  // If 'id' is the song_id (dir name), this call won't work with current /status/<filename>
  console.warn(
    "getSongStatus may require original filename, not song_id, for current /status endpoint"
  );
  return apiRequest<{ status: string; progress?: number }>(`/status/${id}`);
}
