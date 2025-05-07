/**
 * Queue-related API services
 */
import { apiRequest } from "./api";
import {
  KaraokeQueueItem,
  KaraokeQueueItemWithSong,
  AddToKaraokeQueueRequest,
} from "../types/KaraokeQueue";

/**
 * Get the current queue
 */
export async function getQueue() {
  return apiRequest<KaraokeQueueItemWithSong[]>("/queue");
}

/**
 * Get the current playing item
 */
export async function getcurrentSong() {
  return apiRequest<KaraokeQueueItemWithSong | null>("/queue/current");
}

/**
 * Add a song to the queue
 */
export async function addToKaraokeQueue(request: AddToKaraokeQueueRequest) {
  return apiRequest<KaraokeQueueItem>("/queue", {
    method: "POST",
    body: request,
  });
}

/**
 * Remove an item from the queue
 */
export async function removeFromKaraokeQueue(id: string) {
  return apiRequest<{ success: boolean }>(`/queue/${id}`, {
    method: "DELETE",
  });
}

/**
 * Reorder the queue
 */
export async function reorderKaraokeQueue(itemIds: string[]) {
  return apiRequest<KaraokeQueueItemWithSong[]>("/queue/reorder", {
    method: "PUT",
    body: { itemIds },
  });
}

/**
 * Skip to the next item in the queue
 */
export async function skipToNext() {
  return apiRequest<KaraokeQueueItemWithSong | null>("/queue/next", {
    method: "POST",
  });
}

/**
 * Get QR code data for joining the queue
 */
export async function getKaraokeQueueQrCode() {
  return apiRequest<{ qrCodeUrl: string }>("/queue/qr-code");
}
