import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiSend } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:song-recovery");

export interface RecoverableSong {
  id: string;
  title?: string;
  artist?: string;
  videoId?: string | null;
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
      const request: { url: string; body: Record<string, unknown> } =
        song.videoId
          ? {
              url: `songs/${song.id}/replace-youtube`,
              body: {
                video_id: song.videoId,
                title: song.title,
                artist: song.artist,
                engine_type: engineType,
              },
            }
          : {
              url: `songs/${song.id}/reprocess`,
              body: { engine_type: engineType },
            };

      setRecoveringIds((prev) => new Set(prev).add(song.id));
      try {
        await apiSend<unknown, Record<string, unknown>>(
          request.url,
          "post",
          request.body,
        );

        toast.success(
          song.videoId
            ? "Re-download & reprocess job dispatched"
            : "Reprocess job dispatched",
        );
        // Prefix match, so this also invalidates ["songs", song.id].
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        options?.onSuccess?.(song.id);
        return true;
      } catch (error) {
        logger.error("Failed to dispatch recovery job", {
          songId: song.id,
          error,
        });
        toast.error(
          error instanceof Error
            ? error.message
            : "Failed to dispatch recovery job",
        );
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
