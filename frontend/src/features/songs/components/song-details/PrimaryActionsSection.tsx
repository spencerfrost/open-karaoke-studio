import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Play, PlusCircle, Trash2 } from "lucide-react";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAddToKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { toast } from "sonner";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { DeleteSongDialog } from "../DeleteSongDialog";
import { createLogger } from "@/lib/logger";
import { useAuthStore } from "@/stores/authStore";

const logger = createLogger("component:primary-actions");

interface PrimaryActionsSectionProps {
  song: Song;
  onClose: () => void;
  onSongDeleted?: () => void;
}

export const PrimaryActionsSection: React.FC<PrimaryActionsSectionProps> = ({
  song,
  onClose,
  onSongDeleted,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { displayCode, isHost } = useSessionStore();
  const addToQueueMutation = useAddToKaraokeQueue(displayCode || undefined);
  const playFromQueueMutation = usePlayFromKaraokeQueue(
    displayCode || undefined,
  );
  const { useDeleteSong } = useSongs();
  const deleteSongMutation = useDeleteSong();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [isPlayingNow, setIsPlayingNow] = useState(false);

  const handlePlayNow = async () => {
    if (!isHost) {
      toast.error("Only the host device can start playing songs");
      return;
    }

    if (song.status !== "processed") {
      toast.error("Song is not ready for playback yet");
      return;
    }

    setIsPlayingNow(true);
    try {
      // Step 1: Add song to queue
      const queueResponse = await addToQueueMutation.mutateAsync({
        songId: song.id,
        singer: "Unknown Singer", // TODO: Get from user preferences or input
      });

      // Step 2: Immediately play it from queue (moves to position 0)
      await playFromQueueMutation.mutateAsync(String(queueResponse.id));

      // Step 3: Invalidate queue cache to ensure Stage.tsx gets the updated queue
      // This is critical to avoid a race condition where the stale cache causes
      // the wrong song to be loaded
      await queryClient.invalidateQueries({
        queryKey: ["karaoke-queue", displayCode || ""],
      });

      // Step 4: Navigate to stage - the queue will now have the correct song at position 0
      onClose();
      navigate("/stage");
    } catch (error) {
      logger.error("Failed to play song now:", error);
      toast.error("Failed to start playback. Please try again.");
      setIsPlayingNow(false);
    }
  };

  const handleAddToQueue = async () => {
    if (song.status !== "processed") {
      toast.error("Song is not ready for playback yet");
      return;
    }

    try {
      await addToQueueMutation.mutateAsync({
        songId: song.id,
        singer: "Unknown Singer", // TODO: Get from user preferences or input
      });
      queryClient.invalidateQueries({
        queryKey: ["karaoke-queue"],
      });
      sessionWebSocketService.notifyQueueChanged();
    } catch (error) {
      logger.error("Failed to add song to queue:", error);
      toast.error("Failed to add song to queue");
    }
  };

  const isProcessed = song.status === "processed";

  return (
    <div>
      <div className="flex gap-3 flex-col sm:flex-row">
        {/* Play Now button - only show for hosts */}
        {isHost && (
          <Button
            onClick={handlePlayNow}
            disabled={!isProcessed || isPlayingNow}
            className="flex-1 sm:flex-initial sm:min-w-[180px] flex items-center justify-center gap-2"
            size="lg"
          >
            <Play size={18} />
            {isPlayingNow ? "Starting..." : "Play Now"}
          </Button>
        )}

        <Button
          variant="outline"
          onClick={handleAddToQueue}
          disabled={!isProcessed || addToQueueMutation.isPending}
          className="flex-1 sm:flex-initial sm:min-w-[160px] flex items-center justify-center gap-2"
          size="lg"
        >
          <PlusCircle size={18} />
          {addToQueueMutation.isPending ? "Adding..." : "Add to Queue"}
        </Button>

        {isAuthenticated && (
          <DeleteSongDialog
            song={song}
            onConfirm={() => deleteSongMutation.mutateAsync({ id: song.id })}
            isDeleting={deleteSongMutation.isPending}
            onSuccess={onSongDeleted}
            trigger={
              <Button
                variant="outline"
                className="flex-1 sm:flex-initial sm:min-w-[140px] flex items-center justify-center gap-2 border-destructive text-destructive hover:bg-destructive hover:text-white"
                size="lg"
                disabled={deleteSongMutation.isPending}
              >
                <Trash2 size={18} />
                {deleteSongMutation.isPending ? "Removing..." : "Remove"}
              </Button>
            }
          />
        )}
      </div>

      {!isProcessed && (
        <p className="text-sm text-muted-foreground mt-3 text-center">
          Song is still processing and will be available for playback soon
        </p>
      )}

      {!isHost && (
        <p className="text-sm text-muted-foreground mt-3 text-center">
          Only the host device can start playing songs
        </p>
      )}
    </div>
  );
};
