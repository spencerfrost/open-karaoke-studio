/**
 * Queue-related API services
 */
import { apiRequest } from './api';
import { QueueItem, QueueItemWithSong, AddToQueueRequest } from '../types/Queue';

/**
 * Get the current queue
 */
export async function getQueue() {
  return apiRequest<QueueItemWithSong[]>('/queue');
}

/**
 * Get the current playing item
 */
export async function getCurrentItem() {
  return apiRequest<QueueItemWithSong | null>('/queue/current');
}

/**
 * Add a song to the queue
 */
export async function addToQueue(request: AddToQueueRequest) {
  return apiRequest<QueueItem>('/queue', {
    method: 'POST',
    body: request,
  });
}

/**
 * Remove an item from the queue
 */
export async function removeFromQueue(id: string) {
  return apiRequest<{ success: boolean }>(`/queue/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Reorder the queue
 */
export async function reorderQueue(itemIds: string[]) {
  return apiRequest<QueueItemWithSong[]>('/queue/reorder', {
    method: 'PUT',
    body: { itemIds },
  });
}

/**
 * Skip to the next item in the queue
 */
export async function skipToNext() {
  return apiRequest<QueueItemWithSong | null>('/queue/next', {
    method: 'POST',
  });
}

/**
 * Get QR code data for joining the queue
 */
export async function getQueueQrCode() {
  return apiRequest<{ qrCodeUrl: string }>('/queue/qr-code');
}
