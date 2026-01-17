import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Play, PlusCircle, Edit, Trash2 } from "lucide-react";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import { useAddToKaraokeQueue, usePlayFromKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { toast } from "sonner";
import { DeleteSongDialog } from "../DeleteSongDialog";

interface PrimaryActionsSectionProps {
  song: Song;
  onClose: () => void;
  onEditMetadata?: () => void;
  onSongDeleted?: () => void;
}

export const PrimaryActionsSection: React.FC<PrimaryActionsSectionProps> = ({
  song,
  onClose,
  onEditMetadata,
  onSongDeleted,
}) => {
  const navigate = useNavigate();
  const addToQueueMutation = useAddToKaraokeQueue();
  const playFromQueueMutation = usePlayFromKaraokeQueue();
  const { useDeleteSong } = useSongs();
  const deleteSongMutation = useDeleteSong();
  const { displayCode, isHost } = useSessionStore();
  const playerStore = useKaraokePlayerStore();
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

      // Step 3: Clear player playback state
      playerStore.cleanup();
      playerStore.setSongId(song.id, song.duration);

      // Step 4: Navigate to stage
      onClose();
      navigate("/stage");
    } catch (error) {
      console.error("Failed to play song now:", error);
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
    } catch (error) {
      console.error("Failed to add song to queue:", error);
      toast.error("Failed to add song to queue");
    }
  };

  const isProcessed = song.status === "processed";

  return (
    <div className="border-t pt-6 mt-6">
      <div className="flex gap-3 flex-col sm:flex-row">
        {/* Play Now button - only show for hosts */}
        {isHost && (
          <Button
            onClick={handlePlayNow}
            disabled={!isProcessed || isPlayingNow}
            className="flex-1 sm:max-w-[200px] flex items-center gap-2"
            size="lg"
          >
            <Play size={16} />
            {isPlayingNow ? "Starting..." : "Play Now"}
          </Button>
        )}

        <Button
          variant="outline"
          onClick={handleAddToQueue}
          disabled={!isProcessed || addToQueueMutation.isPending}
          className="flex-1 sm:max-w-[160px] flex items-center gap-2"
          size="lg"
        >
          <PlusCircle size={16} />
          {addToQueueMutation.isPending ? "Adding..." : "Add to Queue"}
        </Button>

        {onEditMetadata && (
          <Button
            variant="outline"
            onClick={onEditMetadata}
            className="flex-1 sm:max-w-[160px] flex items-center gap-2"
            size="lg"
          >
            <Edit size={16} />
            Edit Metadata
          </Button>
        )}

        <DeleteSongDialog
          song={song}
          onConfirm={() => deleteSongMutation.mutateAsync({ id: song.id })}
          isDeleting={deleteSongMutation.isPending}
          onSuccess={onSongDeleted}
          trigger={
            <Button
              variant="outline"
              className="flex-1 sm:max-w-[160px] flex items-center gap-2 border-destructive text-destructive hover:bg-destructive hover:text-white"
              size="lg"
              disabled={deleteSongMutation.isPending}
            >
              <Trash2 size={16} />
              {deleteSongMutation.isPending ? "Removing..." : "Remove"}
            </Button>
          }
        />
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
