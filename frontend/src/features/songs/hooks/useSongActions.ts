import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useSongs } from "@/hooks/api/useSongs";
import {
  useAddToKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { useSessionStore } from "@/stores/sessionStore";
import { Song } from "@/types/Song";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:song-actions");

export interface SongActionsConfig {
  onPlay?: (song: Song) => void;
  enableDelete?: boolean;
  enableDetails?: boolean;
}

export const useSongActions = (
  song: Song,
  config: SongActionsConfig = {},
  sessionId?: string,
) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { useDeleteSong } = useSongs();
  const { displayCode, displayName, isHost } = useSessionStore();

  // Use the provided sessionId or fall back to the current session from store
  const currentSessionId = sessionId || (displayCode ? displayCode : undefined);

  const addToKaraokeQueue = useAddToKaraokeQueue(currentSessionId);
  const playFromQueueMutation = usePlayFromKaraokeQueue(currentSessionId);
  const deleteSongMutation = useDeleteSong();

  const handlePlay = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    if (config.onPlay) {
      config.onPlay(song);
      return;
    }

    // If not host, cannot play now
    if (!isHost) {
      toast.error("Only the host device can start playing songs");
      return;
    }

    // If song not processed, cannot play
    if (song.status !== "processed") {
      toast.error("Song is not ready for playback yet");
      return;
    }

    try {
      // Step 1: Add song to queue
      const queueResponse = await addToKaraokeQueue.mutateAsync({
        songId: song.id,
        singer: displayName || "Unknown Singer",
      });

      // Step 2: Immediately play it from queue (moves to position 0)
      await playFromQueueMutation.mutateAsync(String(queueResponse.id));

      // Step 3: Invalidate queue cache to ensure Stage.tsx gets the updated queue
      // This is critical to avoid a race condition where the stale cache causes
      // the wrong song to be loaded
      await queryClient.invalidateQueries({
        queryKey: ["karaoke-queue", currentSessionId],
      });

      // Step 4: Navigate to stage - the queue will now have the correct song at position 0
      navigate("/stage");
    } catch (error) {
      logger.error("Failed to play song now:", error);
      toast.error("Failed to start playback. Please try again.");
    }
  };

  const handleAddToQueue = (singerName: string, sessionCode?: string) => {
    addToKaraokeQueue.mutate(
      { songId: song.id, singer: singerName },
      {
        onSuccess: () => {
          // If we joined a session, we might want to refresh session info
          if (sessionCode) {
            // Could add session refresh logic here if needed
          }
        },
      },
    );
  };

  const handleDelete = () => {
    return deleteSongMutation.mutate({ id: song.id });
  };

  const handleQueueClick = () => {
    // Check if user is in an active session
    if (displayCode && displayName) {
      // User is in session and has a display name, add directly to queue
      handleAddToQueue(displayName);
      return true;
    }
    // User not in session or no display name, need to show join dialog
    return false;
  };

  return {
    handlePlay,
    handleQueueClick,
    handleAddToQueue,
    handleDelete,
    isDeleting: deleteSongMutation.isPending,
    deleteError: deleteSongMutation.isError,
  };
};
