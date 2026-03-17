/**
 * Queue-related API services
 */
import { useApiQuery, useApiMutation } from "./useApi";
import { useAuthStore } from "@/stores/authStore";
import type {
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import {
  KaraokeQueueItemWithSong as KaraokeQueueItem,
  AddToKaraokeQueueRequest,
  KaraokeQueueStateResponse,
} from "@/types/KaraokeQueue";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:queue");

type QueueApiResponse = KaraokeQueueStateResponse | KaraokeQueueItem[];

interface QueuePlayResponse {
  id: string;
  title: string;
  artist: string;
  album?: string | null;
  duration?: number | null;
  coverArt?: string | null;
  syncedLyrics?: string | null;
  plainLyrics?: string | null;
  singer: string;
}

type QueueQueryOptions = Omit<
  UseQueryOptions<
    QueueApiResponse,
    Error,
    QueueApiResponse,
    ["karaoke-queue", string]
  >,
  "queryKey" | "queryFn"
>;

type CurrentSongQueryOptions = Omit<
  UseQueryOptions<
    QueueApiResponse,
    Error,
    QueueApiResponse,
    ["karaoke-queue", string]
  >,
  "queryKey" | "queryFn"
>;

function normalizeQueueState(
  data: QueueApiResponse,
): KaraokeQueueStateResponse {
  if (Array.isArray(data)) {
    const current = data.find((item) => item.position === 0) || null;
    const upcoming = data.filter((item) => item.position !== 0);
    return {
      current,
      upcoming,
      items: data,
    };
  }

  const current = data.current ?? null;
  const upcoming = data.upcoming ?? [];
  const items = data.items ?? [...(current ? [current] : []), ...upcoming];
  const pending = data.pending;

  return {
    current,
    upcoming,
    items,
    ...(pending !== undefined && { pending }),
  };
}

function parseErrorMessage(payload: unknown, fallback: string): string {
  if (
    payload &&
    typeof payload === "object" &&
    "message" in payload &&
    typeof payload.message === "string"
  ) {
    return payload.message;
  }
  return fallback;
}

/**
 * Hook: Get the current queue
 */
export function useQueue(sessionCode?: string, options?: QueueQueryOptions) {
  const query = useApiQuery<QueueApiResponse, ["karaoke-queue", string]>(
    ["karaoke-queue", sessionCode || ""],
    `karaoke-queue${sessionCode ? `?session_code=${sessionCode}` : ""}`,
    options,
  );

  return {
    ...query,
    data: query.data ? normalizeQueueState(query.data) : undefined,
  };
}

/**
 * Hook: Get the current playing item
 */
export function useCurrentSong(
  sessionCode?: string,
  options?: CurrentSongQueryOptions,
) {
  const queue = useQueue(sessionCode, options);
  return {
    ...queue,
    data: queue.data?.current ?? null,
  };
}

/**
 * Hook: Add a song to the queue
 */
export function useAddToKaraokeQueue(
  sessionCode?: string,
  options?: Omit<
    UseMutationOptions<
      KaraokeQueueItem,
      Error,
      AddToKaraokeQueueRequest,
      unknown
    >,
    "mutationFn"
  >,
) {
  return useApiMutation<KaraokeQueueItem, AddToKaraokeQueueRequest>(
    `karaoke-queue${sessionCode ? `?session_code=${sessionCode}` : ""}`,
    "post",
    options,
  );
}

/**
 * Hook: Remove an item from the queue
 */
import { useMutation } from "@tanstack/react-query";
export function useRemoveFromKaraokeQueue(
  sessionCode?: string,
  options?: Omit<
    UseMutationOptions<{ success: boolean }, Error, string, unknown>,
    "mutationFn"
  >,
) {
  // Custom mutation for dynamic URL based on id
  return useMutation<{ success: boolean }, Error, string, unknown>({
    mutationFn: async (id: string) => {
      const url = `/api/karaoke-queue/${id}${sessionCode ? `?session_code=${sessionCode}` : ""}`;
      const token = useAuthStore.getState().token;
      const response = await fetch(url, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errorData: unknown = await response.json();
          errorMessage = parseErrorMessage(errorData, errorMessage);
        } catch (jsonError: unknown) {
          logger.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }
      return await response.json();
    },
    ...options,
  });
}

/**
 * Hook: Play a song from the queue (removes from queue and loads into player)
 */
export function usePlayFromKaraokeQueue(
  sessionCode?: string,
  options?: Omit<
    UseMutationOptions<QueuePlayResponse, Error, string, unknown>,
    "mutationFn"
  >,
) {
  return useMutation<QueuePlayResponse, Error, string, unknown>({
    mutationFn: async (id: string) => {
      const url = `/api/karaoke-queue/${id}/play${sessionCode ? `?session_code=${sessionCode}` : ""}`;
      const token = useAuthStore.getState().token;
      const response = await fetch(url, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errorData: unknown = await response.json();
          errorMessage = parseErrorMessage(errorData, errorMessage);
        } catch (jsonError: unknown) {
          logger.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }
      return await response.json();
    },
    ...options,
  });
}

/**
 * Hook: Skip to the next item in the queue
 */
export function useSkipToNext(
  options?: Omit<
    UseMutationOptions<KaraokeQueueItem | null, Error, void, unknown>,
    "mutationFn"
  >,
) {
  return useApiMutation<KaraokeQueueItem | null, void>(
    "queue/next",
    "post",
    options,
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
  >,
) {
  return useApiQuery<{ qrCodeUrl: string }, ["queue", "qr-code"]>(
    ["queue", "qr-code"],
    "queue/qr-code",
    options,
  );
}
