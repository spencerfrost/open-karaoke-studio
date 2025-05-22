/**
 * Queue-related API services
 */
import { useApiQuery, useApiMutation } from "./useApi";
import type {
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import {
  KaraokeQueueItem,
  KaraokeQueueItemWithSong,
  AddToKaraokeQueueRequest,
} from "../types/KaraokeQueue";

/**
 * Hook: Get the current queue
 */
export function useQueue(
  options?: Omit<
    UseQueryOptions<
      KaraokeQueueItemWithSong[],
      Error,
      KaraokeQueueItemWithSong[],
      ["queue"]
    >,
    "queryKey" | "queryFn"
  >
) {
  return useApiQuery<KaraokeQueueItemWithSong[], ["queue"]>(
    ["queue"],
    "queue",
    options
  );
}

/**
 * Hook: Get the current playing item
 */
export function useCurrentSong(
  options?: Omit<
    UseQueryOptions<
      KaraokeQueueItemWithSong | null,
      Error,
      KaraokeQueueItemWithSong | null,
      ["queue", "current"]
    >,
    "queryKey" | "queryFn"
  >
) {
  return useApiQuery<KaraokeQueueItemWithSong | null, ["queue", "current"]>(
    ["queue", "current"],
    "queue/current",
    options
  );
}

/**
 * Hook: Add a song to the queue
 */
export function useAddToKaraokeQueue(
  options?: Omit<
    UseMutationOptions<
      KaraokeQueueItem,
      Error,
      AddToKaraokeQueueRequest,
      unknown
    >,
    "mutationFn"
  >
) {
  return useApiMutation<KaraokeQueueItem, AddToKaraokeQueueRequest>(
    "queue",
    "post",
    options
  );
}

/**
 * Hook: Remove an item from the queue
 */
import { useMutation } from "@tanstack/react-query";
export function useRemoveFromKaraokeQueue(
  options?: Omit<
    UseMutationOptions<{ success: boolean }, Error, string, unknown>,
    "mutationFn"
  >
) {
  // Custom mutation for dynamic URL based on id
  return useMutation<{ success: boolean }, Error, string, unknown>({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/queue/${id}`, { method: "DELETE" });
      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errorData: any = await response.json();
          errorMessage = errorData?.message || errorMessage;
        } catch (jsonError: any) {
          console.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }
      return await response.json();
    },
    ...options,
  });
}

/**
 * Hook: Reorder the queue
 */
export function useReorderKaraokeQueue(
  options?: Omit<
    UseMutationOptions<
      KaraokeQueueItemWithSong[],
      Error,
      { itemIds: string[] },
      unknown
    >,
    "mutationFn"
  >
) {
  return useApiMutation<KaraokeQueueItemWithSong[], { itemIds: string[] }>(
    "queue/reorder",
    "put",
    options
  );
}

/**
 * Hook: Skip to the next item in the queue
 */
export function useSkipToNext(
  options?: Omit<
    UseMutationOptions<KaraokeQueueItemWithSong | null, Error, void, unknown>,
    "mutationFn"
  >
) {
  return useApiMutation<KaraokeQueueItemWithSong | null, void>(
    "queue/next",
    "post",
    options
  );
}

/**
 * Hook: Get QR code data for joining the queue
 */
export function useKaraokeQueueQrCode(
  options?: Omit<
    UseQueryOptions<
      { qrCodeUrl: string },
      Error,
      { qrCodeUrl: string },
      ["queue", "qr-code"]
    >,
    "queryKey" | "queryFn"
  >
) {
  return useApiQuery<{ qrCodeUrl: string }, ["queue", "qr-code"]>(
    ["queue", "qr-code"],
    "queue/qr-code",
    options
  );
}
