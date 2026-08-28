import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getAuthHeaders, handleUnauthorized } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:song-recovery");

export interface RecoverableSong {
  id: string;
  title?: string;
  artist?: string;
  videoId?: string | null;
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data?.detail) return data.detail;
  } catch {
    // fall through to status-based message
  }
  return `Request failed with status ${response.status}`;
}

/**
 * Shared retry/recovery flow for a song stuck in "error" (or otherwise
 * incomplete): re-download from YouTube via /replace-youtube when a
 * videoId is known, else /reprocess against the existing original.mp3.
 */
export function useSongRecovery(options?: {
  engineType?: string;
  onSuccess?: (songId: string) => void;
}) {
  const engineType = options?.engineType ?? "three_track";
  const queryClient = useQueryClient();
  const [recoveringIds, setRecoveringIds] = useState<Set<string>>(new Set());

  const recoverSong = useCallback(
    async (song: RecoverableSong): Promise<boolean> => {
      setRecoveringIds((prev) => new Set(prev).add(song.id));
      try {
        const response = song.videoId
          ? await fetch(`/api/songs/${song.id}/replace-youtube`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                ...getAuthHeaders(),
              },
              body: JSON.stringify({
                video_id: song.videoId,
                title: song.title,
                artist: song.artist,
                engine_type: engineType,
              }),
            })
          : await fetch(`/api/songs/${song.id}/reprocess`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                ...getAuthHeaders(),
              },
              body: JSON.stringify({ engine_type: engineType }),
            });

        if (!response.ok) {
          handleUnauthorized(response);
          const message = await parseErrorMessage(response);
          toast.error(message);
          return false;
        }

        toast.success(
          song.videoId
            ? "Re-download & reprocess job dispatched"
            : "Reprocess job dispatched",
        );
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        queryClient.invalidateQueries({ queryKey: ["songs", song.id] });
        options?.onSuccess?.(song.id);
        return true;
      } catch (error) {
        logger.error("Failed to dispatch recovery job", {
          songId: song.id,
          error,
        });
        toast.error("Failed to dispatch recovery job");
        return false;
      } finally {
        setRecoveringIds((prev) => {
          const next = new Set(prev);
          next.delete(song.id);
          return next;
        });
      }
    },
    [engineType, queryClient, options],
  );

  const isRecovering = useCallback(
    (songId: string) => recoveringIds.has(songId),
    [recoveringIds],
  );

  return { recoverSong, isRecovering, recoveringIds };
}
