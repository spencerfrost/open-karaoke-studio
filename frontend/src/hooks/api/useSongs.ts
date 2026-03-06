import { useCallback } from "react";
import {
  useApiQuery,
  useApiMutation,
  uploadFile,
  handleUnauthorized,
} from "./useApi";
import { ChordEvent, Song, SongProcessingStatus } from "../../types/Song";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { createLogger } from "@/lib/logger";
import { useAuthStore } from "@/stores/authStore";

const logger = createLogger("hook:songs");

// Query keys for React Query
const QUERY_KEYS = {
  songs: ["songs"] as const,
  song: (id: string) => ["songs", id] as const,
  songStatus: (id: string) => ["songs", id, "status"] as const,
  songLyrics: (id: string) => ["songs", id, "lyrics"] as const,
  songChords: (id: string) => ["songs", id, "chords"] as const,
  metadata: ["metadata", "search"] as const,
};

// Helper function to replace URL parameters
const formatUrl = (url: string, params: Record<string, string>) => {
  let formattedUrl = url;
  Object.entries(params).forEach(([key, value]) => {
    formattedUrl = formattedUrl.replace(`:${key}`, value);
  });
  return formattedUrl;
};

/**
 * Hook for interacting with song-related API endpoints
 */
export function useSongs() {
  const queryClient = useQueryClient();

  // ===== Queries =====

  /**
   * Get songs in the library with flexible query params (limit, offset, sort_by, direction, etc)
   * Pass params as an object: { limit, offset, sort_by, direction, ... }
   * If 'q' parameter is provided, automatically routes to the search endpoint
   */
  const useSongs = (params: Record<string, any> = {}, options = {}) => {
    // If search query is provided, use the search endpoint
    const isSearch = params.q && params.q.trim().length > 0;
    const endpoint = isSearch ? "songs/search" : "songs";

    const queryString = Object.keys(params).length
      ? `${endpoint}?${new URLSearchParams(params).toString()}`
      : endpoint;

    // Use params as part of the query key for caching, include endpoint type
    const queryKey = ["songs", isSearch ? "search" : "list", params];

    // Use a custom query function that handles different response formats
    const queryFn = async () => {
      const response = await fetch(`/api/${queryString}`, {
        credentials: "include",
      });

      if (!response.ok) {
        let errorMessage = `HTTP error! Status: ${response.status}`;
        try {
          const contentType = response.headers.get("Content-Type") ?? "";
          if (contentType.includes("application/json")) {
            const errorData = await response.json();
            errorMessage =
              errorData?.error || errorData?.message || errorMessage;
          }
        } catch (jsonError) {
          logger.error("Error parsing error response:", jsonError);
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();

      // If it's a search response, extract the songs array
      if (isSearch && data.songs) {
        return data.songs;
      }

      // Otherwise return the data as-is (should be a songs array)
      return data;
    };

    return useQuery<Song[], typeof queryKey>({
      queryKey,
      queryFn,
      ...options,
    });
  };

  /**
   * Get a specific song by ID
   */
  const useSong = (id: string, options = {}) => {
    return useApiQuery<Song, ReturnType<typeof QUERY_KEYS.song>>(
      QUERY_KEYS.song(id),
      `songs/${id}`,
      {
        enabled: !!id,
        ...options,
      },
    );
  };

  /**
   * Get song processing status
   */
  const useSongStatus = (id: string, options = {}) => {
    return useApiQuery<
      SongProcessingStatus,
      ReturnType<typeof QUERY_KEYS.songStatus>
    >(QUERY_KEYS.songStatus(id), `status/${id}`, {
      enabled: !!id,
      refetchInterval: (query) =>
        query.state.data &&
        (query.state.data.status === "processing" ||
          query.state.data.status === "queued")
          ? 2000
          : false,
      ...options,
    });
  };

  /**
   * Get precomputed chord events for a song.
   * Returns empty array when chord data is unavailable (404).
   */
  const useSongChords = (id: string, options = {}) => {
    return useQuery<ChordEvent[], ReturnType<typeof QUERY_KEYS.songChords>>({
      queryKey: QUERY_KEYS.songChords(id),
      enabled: !!id,
      queryFn: async () => {
        const response = await fetch(`/api/songs/${id}/chords`, {
          credentials: "include",
        });

        if (response.status === 404) {
          return [];
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch song chords: ${response.status}`);
        }

        const data: unknown = await response.json();
        if (!Array.isArray(data)) {
          return [];
        }

        return data
          .filter(
            (item): item is ChordEvent =>
              typeof item === "object" &&
              item !== null &&
              typeof (item as ChordEvent).time === "number" &&
              typeof (item as ChordEvent).chord === "string",
          )
          .sort((a, b) => a.time - b.time);
      },
      ...options,
    });
  };

  // ===== Mutations =====
  /**
   * Create a new song
   */
  const useCreateSong = () => {
    return useApiMutation<Song, Partial<Song>>("songs", "post", {
      onMutate: async () => {
        await queryClient.cancelQueries({ queryKey: ["songs"] });
        return {};
      },
      onError: () => {
        // Invalidate to refetch fresh data on error
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      onSettled: () => {
        // Refetch to ensure server state
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      mutationFn: async (data) => {
        const response = await fetch("/api/songs", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
          credentials: "include",
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || `Failed to create song: ${response.status}`,
          );
        }
        return response.json();
      },
    });
  };

  /**
   * Update a song
   */
  const useUpdateSong = () => {
    return useApiMutation<Song, Partial<Song> & { id: string }>(
      "songs/:id",
      "patch",
      {
        onMutate: async (variables) => {
          const { id, ...updates } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });

          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(
            QUERY_KEYS.song(id),
          );

          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(QUERY_KEYS.song(id), {
              ...previousSong,
              ...updates,
            });

            // Note: We don't optimistically update song lists due to complex query key structure
            // The cache will be properly updated via invalidation on success
          }

          return { previousSong };
        },
        onError: (_err, variables, context: unknown) => {
          const ctx = context as { previousSong?: Song } | undefined;
          if (ctx?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              ctx.previousSong,
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.song(variables.id),
          });
          queryClient.invalidateQueries({ queryKey: ["songs"] });
        },
        mutationFn: async (data) => {
          const { id, ...updates } = data;
          const url = formatUrl("songs/:id", { id });
          const response = await fetch(`/api/${url}`, {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(updates),
            credentials: "include",
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(
              errorData.error || `Failed to update song: ${response.status}`,
            );
          }

          return response.json();
        },
      },
    );
  };

  /**
   * Update song metadata
   */
  const useUpdateSongMetadata = () => {
    return useApiMutation<Song, { id: string } & Partial<Song>>(
      "songs/:id/metadata",
      "patch",
      {
        onMutate: async (variables) => {
          const { id, ...metadata } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });

          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(
            QUERY_KEYS.song(id),
          );

          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(QUERY_KEYS.song(id), {
              ...previousSong,
              ...metadata,
            });

            // Note: We don't optimistically update song lists due to complex query key structure
            // The cache will be properly updated via invalidation on success
          }

          return { previousSong };
        },
        onError: (_err, variables, context: unknown) => {
          // If the mutation fails, roll back to the previous song
          const typedContext = context as { previousSong?: Song } | undefined;
          if (typedContext?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              typedContext.previousSong,
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.song(variables.id),
          });
          queryClient.invalidateQueries({ queryKey: ["songs"] });
        },
        mutationFn: async (data) => {
          const { id, ...metadata } = data;
          const url = formatUrl("songs/:id/metadata", { id });
          const response = await fetch(`/api/${url}`, {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(metadata),
            credentials: "include",
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(
              errorData.error ||
                `Failed to update metadata: ${response.status}`,
            );
          }

          return response.json();
        },
      },
    );
  };

  /**
   * Update iTunes metadata for a song
   */
  const useUpdateItunesMetadata = () => {
    return useApiMutation<
      Song,
      {
        id: string;
        itunesTrackId?: number;
        itunesArtistId?: number;
        itunesCollectionId?: number;
        trackTimeMillis?: number;
        itunesExplicit?: boolean;
        itunesPreviewUrl?: string;
        itunesArtworkUrls?: {
          60?: string;
          100?: string;
          600?: string;
        };
      }
    >("songs/:id/metadata/itunes", "patch", {
      onMutate: async (variables) => {
        const { id, ...metadata } = variables;
        await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });

        const previousSong = queryClient.getQueryData<Song>(
          QUERY_KEYS.song(id),
        );

        if (previousSong) {
          queryClient.setQueryData<Song>(QUERY_KEYS.song(id), {
            ...previousSong,
            ...metadata,
          });
        }

        return { previousSong };
      },
      onError: (_err, variables, context: unknown) => {
        const ctx = context as { previousSong?: Song } | undefined;
        if (ctx?.previousSong) {
          queryClient.setQueryData(
            QUERY_KEYS.song(variables.id),
            ctx.previousSong,
          );
        }
      },
      onSettled: (_data, _error, variables) => {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.song(variables.id),
        });
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      mutationFn: async (data) => {
        const { id, ...metadata } = data;
        const url = formatUrl("songs/:id/metadata/itunes", { id });
        const response = await fetch(`/api/${url}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(metadata),
          credentials: "include",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error ||
              `Failed to update iTunes metadata: ${response.status}`,
          );
        }

        return response.json();
      },
    });
  };

  /**
   * Update YouTube metadata for a song
   */
  const useUpdateYoutubeMetadata = () => {
    return useApiMutation<
      Song,
      {
        id: string;
        youtubeDuration?: number;
        youtubeThumbnailUrls?: {
          default?: string;
          medium?: string;
          high?: string;
          standard?: string;
          maxres?: string;
        };
        youtubeTags?: string[];
        youtubeCategories?: string[];
        youtubeChannelId?: string;
        youtubeChannelName?: string;
      }
    >("songs/:id/metadata/youtube", "patch", {
      onMutate: async (variables) => {
        const { id, ...metadata } = variables;
        await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });

        const previousSong = queryClient.getQueryData<Song>(
          QUERY_KEYS.song(id),
        );

        if (previousSong) {
          queryClient.setQueryData<Song>(QUERY_KEYS.song(id), {
            ...previousSong,
            ...metadata,
          });
        }

        return { previousSong };
      },
      onError: (_err, variables, context: unknown) => {
        const ctx = context as { previousSong?: Song } | undefined;
        if (ctx?.previousSong) {
          queryClient.setQueryData(
            QUERY_KEYS.song(variables.id),
            ctx.previousSong,
          );
        }
      },
      onSettled: (_data, _error, variables) => {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.song(variables.id),
        });
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      mutationFn: async (data) => {
        const { id, ...metadata } = data;
        const url = formatUrl("songs/:id/metadata/youtube", { id });
        const response = await fetch(`/api/${url}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(metadata),
          credentials: "include",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error ||
              `Failed to update YouTube metadata: ${response.status}`,
          );
        }

        return response.json();
      },
    });
  };

  /**
   * Delete a song
   */
  const useDeleteSong = () => {
    return useApiMutation<void, { id: string }>("songs/:id", "delete", {
      onMutate: async () => {
        // Cancel all song-related queries to prevent race conditions
        await queryClient.cancelQueries({ queryKey: ["songs"] });
        await queryClient.cancelQueries({ queryKey: ["artists"] });
        await queryClient.cancelQueries({ queryKey: ["artist-songs"] });
        return {};
      },
      onSuccess: (_data, variables) => {
        // Remove the specific song from all caches
        queryClient.removeQueries({ queryKey: QUERY_KEYS.song(variables.id) });
      },
      onSettled: () => {
        // Invalidate all queries after mutation completes (success or error)
        // Using a small delay to allow UI to update first
        setTimeout(() => {
          queryClient.invalidateQueries({ queryKey: ["songs"] });
          queryClient.invalidateQueries({ queryKey: ["artists"] });
          queryClient.invalidateQueries({ queryKey: ["artist-songs"] });
        }, 100);
      },
      mutationFn: async (data) => {
        const url = formatUrl("songs/:id", { id: data.id });
        const token = useAuthStore.getState().token;
        logger.debug(
          "DELETE %s — token present: %s, token prefix: %s",
          url,
          !!token,
          token?.substring(0, 20),
        );
        const response = await fetch(`/api/${url}`, {
          method: "DELETE",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
        });

        if (!response.ok) {
          handleUnauthorized(response);
          const errorData = await response.json();
          throw new Error(
            errorData.detail ||
              errorData.error ||
              `Failed to delete song: ${response.status}`,
          );
        }

        return;
      },
    });
  };

  /**
   * Reprocess a song with a different separation engine
   */
  const useReprocessSong = () => {
    return useApiMutation<
      { jobId: string; status: string; message: string },
      { id: string; engine_type: string }
    >("songs/:id/reprocess", "post", {
      onMutate: async (variables) => {
        await queryClient.cancelQueries({
          queryKey: QUERY_KEYS.song(variables.id),
        });
        return {};
      },
      onSettled: (_data, _error, variables) => {
        // Invalidate song queries to refresh status
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.song(variables.id),
        });
        queryClient.invalidateQueries({ queryKey: ["songs"] });
      },
      mutationFn: async (data) => {
        const { id, engine_type } = data;
        const token = useAuthStore.getState().token;
        const response = await fetch(`/api/songs/${id}/reprocess`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ engine_type }),
          credentials: "include",
        });

        if (!response.ok) {
          handleUnauthorized(response);
          const errorData = await response.json();
          throw new Error(
            errorData.detail || `Failed to reprocess: ${response.status}`,
          );
        }

        return response.json();
      },
    });
  };

  /**
   * Reprocess all songs (admin) — POST /api/songs/reprocess-all
   * This endpoint is auth-protected; include Authorization header when available.
   */
  const useReprocessAllSongs = () => {
    return useApiMutation<
      { jobsCreated: number; skipped: number; message: string },
      void
    >("songs/reprocess-all", "post", {
      mutationFn: async () => {
        const token = useAuthStore.getState().token;
        const response = await fetch(`/api/songs/reprocess-all`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
        });

        if (!response.ok) {
          handleUnauthorized(response);
          const errorData = await response.json();
          throw new Error(
            errorData?.detail ||
              errorData?.error ||
              `Failed to reprocess-all: ${response.status}`,
          );
        }

        return response.json();
      },
    });
  };

  /**
   * Get rich metadata for a song (includes all iTunes/YouTube metadata)
   */
  const useRichSongMetadata = (id: string, options = {}) => {
    return useApiQuery<
      Song & {
        metadataQuality?: {
          hasItunes: boolean;
          hasYoutube: boolean;
          hasArtwork: boolean;
          hasThumbnails: boolean;
          completeness: number; // 0-100
        };
      },
      ReturnType<typeof QUERY_KEYS.song>
    >(QUERY_KEYS.song(id), `songs/${id}?include_metadata=true`, {
      enabled: !!id,
      ...options,
    });
  };

  // ===== Utility Functions =====

  /**
   * Get the best available artwork URL for a song with priority fallbacks
   */
  const getArtworkUrl = useCallback(
    (
      song: Song,
      size: "small" | "medium" | "large" = "medium",
    ): string | null => {
      // Priority: Backend API thumbnail endpoint > iTunes artwork > YouTube thumbnail URLs
      if (song.thumbnail) {
        // Use the backend API endpoint for thumbnails (auto-detects format)
        return `/api/songs/${song.id}/thumbnail`;
      }

      // YouTube thumbnail URLs (external)
      if (song.youtubeThumbnailUrls) {
        switch (size) {
          case "large":
            if (song.youtubeThumbnailUrls.maxres)
              return song.youtubeThumbnailUrls.maxres;
            if (song.youtubeThumbnailUrls.standard)
              return song.youtubeThumbnailUrls.standard;
            if (song.youtubeThumbnailUrls.high)
              return song.youtubeThumbnailUrls.high;
            if (song.youtubeThumbnailUrls.medium)
              return song.youtubeThumbnailUrls.medium;
            if (song.youtubeThumbnailUrls.default)
              return song.youtubeThumbnailUrls.default;
            break;
          case "medium":
            if (song.youtubeThumbnailUrls.high)
              return song.youtubeThumbnailUrls.high;
            if (song.youtubeThumbnailUrls.medium)
              return song.youtubeThumbnailUrls.medium;
            if (song.youtubeThumbnailUrls.standard)
              return song.youtubeThumbnailUrls.standard;
            if (song.youtubeThumbnailUrls.default)
              return song.youtubeThumbnailUrls.default;
            break;
          case "small":
            if (song.youtubeThumbnailUrls.medium)
              return song.youtubeThumbnailUrls.medium;
            if (song.youtubeThumbnailUrls.default)
              return song.youtubeThumbnailUrls.default;
            if (song.youtubeThumbnailUrls.high)
              return song.youtubeThumbnailUrls.high;
            break;
        }
      }
      return null;
    },
    [],
  );

  /**
   * Get a playback URL for a given song track type
   */
  const getAudioUrl = useCallback(
    (
      songId: string,
      trackType: "vocals" | "instrumental" | "original",
    ): string => {
      // Use the backend API endpoint for audio
      return `/api/songs/${songId}/download/${trackType}`;
    },
    [],
  );

  /**
   * Upload a song file for processing
   */
  const uploadSong = useCallback(
    async (file: File, metadata?: Record<string, unknown>) => {
      return uploadFile<Song>("songs/upload", file, metadata);
    },
    [],
  );

  /**
   * Download vocal track
   */
  const downloadVocals = useCallback(
    async (songId: string, filename?: string) => {
      const url = `/api/songs/${songId}/download/vocals`;
      await downloadFile(url, filename ?? `vocals-${songId}.mp3`);
    },
    [],
  );

  /**
   * Download instrumental track
   */
  const downloadInstrumental = useCallback(
    async (songId: string, filename?: string) => {
      const url = `/api/songs/${songId}/download/instrumental`;
      await downloadFile(url, filename ?? `instrumental-${songId}.mp3`);
    },
    [],
  );

  /**
   * Download original track
   */
  const downloadOriginal = useCallback(
    async (songId: string, filename?: string) => {
      const url = `/api/songs/${songId}/download/original`;
      await downloadFile(url, filename ?? `original-${songId}.mp3`);
    },
    [],
  );

  /**
   * Fetch an audio file as an ArrayBuffer for Web Audio API
   */
  const fetchAudioBuffer = useCallback(
    async (url: string): Promise<ArrayBuffer> => {
      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch audio file");
      return await response.arrayBuffer();
    },
    [],
  );

  return {
    // Queries
    useSongs,
    useSong,
    useSongStatus,
    useSongChords,
    useRichSongMetadata,

    // Mutations
    useCreateSong,
    useUpdateSong,
    useUpdateSongMetadata,
    useUpdateItunesMetadata,
    useUpdateYoutubeMetadata,
    useDeleteSong,
    useReprocessSong,
    useReprocessAllSongs,

    // Utility functions
    getAudioUrl,
    uploadSong,
    downloadVocals,
    downloadInstrumental,
    downloadOriginal,
    fetchAudioBuffer,
    getArtworkUrl,
  };
}

/**
 * Helper function to download a file
 */
async function downloadFile(endpoint: string, filename: string): Promise<void> {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    logger.error("Download error:", error);
    throw error;
  }
}
