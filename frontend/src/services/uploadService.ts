/**
 * Upload-related API services
 */
import { uploadFile, apiRequest } from './api';
import { SongProcessingRequest, SongProcessingStatus } from '../types/Song';

/**
 * Upload and process an audio file
 */
export async function uploadAndProcessAudio(file: File, metadata?: { title?: string; artist?: string }) {
  return uploadFile<{ id: string; status: string }>('/process', file, metadata);
}

/**
 * Process a YouTube video
 */
export async function processYouTubeVideo(youtubeUrl: string, metadata?: { title?: string; artist?: string }) {
  return apiRequest<{ id: string; status: string }>('/process-youtube', {
    method: 'POST',
    body: {
      url: youtubeUrl,
      ...metadata,
    },
  });
}

/**
 * Get the status of a processing task
 */
export async function getProcessingStatus(taskId: string) {
  return apiRequest<SongProcessingStatus>(`/status/${taskId}`);
}

/**
 * Get all currently processing tasks
 */
export async function getProcessingQueue() {
  return apiRequest<SongProcessingStatus[]>('/processing-queue');
}

/**
 * Cancel a processing task
 */
export async function cancelProcessing(taskId: string) {
  return apiRequest<{ success: boolean }>(`/processing/${taskId}/cancel`, {
    method: 'POST',
  });
}
