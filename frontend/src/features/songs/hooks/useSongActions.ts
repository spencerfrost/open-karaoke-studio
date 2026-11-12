import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useSongs } from "@/hooks/api/useSongs";
import {
  useAddToKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { useSessionStore } from "@/stores/sessionStore";
import { useAccess } from "@/hooks/useAccess";
import { Song } from "@/types/Song";
import { toast } from "sonner";
import { useStageShell } from "@/features/stage";
import { createLogger } from "@/lib/logger";
import { useQueueSong } from "./useQueueSong";

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
  const { sessionId: storeSessionId } = useSessionStore();
  const access = useAccess();

  // Use the provided sessionId or fall back to the current session from store
  const currentSessionId = sessionId ?? storeSessionId ?? undefined;

  const addToKaraokeQueue = useAddToKaraokeQueue(currentSessionId);
  const playFromQueueMutation = usePlayFromKaraokeQueue(currentSessionId);
  const deleteSongMutation = useDeleteSong();
  const { queueSong, addToQueue } = useQueueSong(currentSessionId);

  /**
   * Queue this song and start it immediately, under an explicit name.
   *
   * On the stage the name comes from the confirm screen. Everywhere else it
   * falls back to the session's display name, which is how it has always
   * worked — and why every stage walk-up used to land in the queue as the host.
   *
   * Resolves true once the song has started; failures toast and resolve false.
   */
  const handlePlayAs = async (singerName?: string): Promise<boolean> => {
    // If not host, cannot play now
    if (!access.isStageDevice) {
      toast.error("Only the host device can start playing songs");
      return false;
    }

    // If song not processed, cannot play
    if (song.status !== "processed") {
      toast.error("Song is not ready for playback yet");
      return false;
    }

    try {
      // Step 1: Add song to queue
      const queueResponse = await addToKaraokeQueue.mutateAsync({
        songId: song.id,
        singer: singerName?.trim() || access.singerName || "Unknown Singer",
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
      return true;
    } catch (error) {
      logger.error("Failed to play song now:", error);
      toast.error("Failed to start playback. Please try again.");
      return false;
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

  const handleAddToQueue = (singerName: string) => addToQueue(song, singerName);

  const handleDelete = () => {
    return deleteSongMutation.mutate({ id: song.id });
  };

  /** See useQueueSong: `pickSinger` opens the caller's QueueSingerDialog. */
  const handleQueueClick = (pickSinger: () => void) =>
    queueSong(song, pickSinger);

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
