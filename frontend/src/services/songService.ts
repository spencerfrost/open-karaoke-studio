/**
 * Song-related API services
 */
import { apiRequest, downloadFile } from './api';
import { Song } from '../types/Song';

/**
 * Get all songs in the library
 */
export async function getSongs() {
  return apiRequest<Song[]>('/songs');
}

/**
 * Get a specific song by ID
 */
export async function getSongById(id: string) {
  return apiRequest<Song>(`/songs/${id}`);
}

/**
 * Update a song
 */
export async function updateSong(id: string, updates: Partial<Song>) {
  return apiRequest<Song>(`/songs/${id}`, {
    method: 'PUT',
    body: updates,
  });
}

/**
 * Delete a song
 */
export async function deleteSong(id: string) {
  return apiRequest<{ success: boolean }>(`/songs/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Toggle favorite status of a song
 */
export async function toggleFavorite(id: string, isFavorite: boolean) {
  return apiRequest<Song>(`/songs/${id}/favorite`, {
    method: 'PUT',
    body: { favorite: isFavorite },
  });
}

/**
 * Download vocal track
 */
export async function downloadVocals(songId: string, filename: string) {
  return downloadFile(`/download/${songId}/vocals`, filename || `vocals-${songId}.mp3`);
}

/**
 * Download instrumental track
 */
export async function downloadInstrumental(songId: string, filename: string) {
  return downloadFile(`/download/${songId}/instrumental`, filename || `instrumental-${songId}.mp3`);
}

/**
 * Download original track
 */
export async function downloadOriginal(songId: string, filename: string) {
  return downloadFile(`/download/${songId}/original`, filename || `original-${songId}.mp3`);
}

/**
 * Get song processing status
 */
export async function getSongStatus(id: string) {
  return apiRequest<{ status: string; progress?: number }>(`/status/${id}`);
}
