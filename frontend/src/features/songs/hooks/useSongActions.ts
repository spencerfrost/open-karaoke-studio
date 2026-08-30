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
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { useStageShell } from "@/features/stage";
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
  // Null everywhere but the stage. Its presence is what turns "play this" into
  // "ask who is singing first" without every card having to know where it is.
  const shell = useStageShell();
  const queryClient = useQueryClient();
  const { useDeleteSong } = useSongs();
  const { displayCode, displayName, isStageDevice } = useSessionStore();

  // Use the provided sessionId or fall back to the current session from store
  const currentSessionId = sessionId || (displayCode ? displayCode : undefined);

  const addToKaraokeQueue = useAddToKaraokeQueue(currentSessionId);
  const playFromQueueMutation = usePlayFromKaraokeQueue(currentSessionId);
  const deleteSongMutation = useDeleteSong();

  /**
   * Queue this song and start it immediately, under an explicit name.
   *
   * On the stage the name comes from the confirm screen. Everywhere else it
   * falls back to the session's display name, which is how it has always
   * worked — and why every stage walk-up used to land in the queue as the host.
   */
  const handlePlayAs = async (singerName?: string) => {
    // If not host, cannot play now
    if (!isStageDevice) {
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
        singer: singerName?.trim() || displayName || "Unknown Singer",
      });

      // Step 2: Immediately play it from queue (moves to position 0)
      await playFromQueueMutation.mutateAsync(String(queueResponse.id));

      // Step 3: Invalidate queue cache to ensure Stage.tsx gets the updated queue
      // This is critical to avoid a race condition where the stale cache causes
      // the wrong song to be loaded
      await queryClient.invalidateQueries({
        queryKey: ["karaoke-queue", currentSessionId],
      });

      // Step 4: Show the player - the queue now has the correct song at position 0.
      // Inside stage mode that is a screen change, not a navigation: the shell
      // is already the player and must not remount.
      if (shell) shell.openPerformance();
      else navigate("/stage");
    } catch (error) {
      logger.error("Failed to play song now:", error);
      toast.error("Failed to start playback. Please try again.");
    }
  };

  const handlePlay = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    if (config.onPlay) {
      config.onPlay(song);
      return;
    }

    // The stage always asks who is singing before it starts anything.
    if (shell) {
      shell.openConfirm(song);
      return;
    }

    await handlePlayAs();
  };

  const handleAddToQueue = (singerName: string) => {
    addToKaraokeQueue.mutate(
      { songId: song.id, singer: singerName },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({
            queryKey: ["karaoke-queue"],
          });
          sessionWebSocketService.notifyQueueChanged();
        },
      },
    );
  };

  const handleDelete = () => {
    return deleteSongMutation.mutate({ id: song.id });
  };

  const handleQueueClick = () => {
    // On the stage, queueing goes through the confirm screen so the singer is a
    // person rather than whoever happens to own the session.
    if (shell) {
      shell.openConfirm(song);
      return true;
    }

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
    handlePlayAs,
    handleQueueClick,
    handleAddToQueue,
    handleDelete,
    isDeleting: deleteSongMutation.isPending,
    deleteError: deleteSongMutation.isError,
  };
};
