import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Play, PlusCircle, Edit, Trash2 } from "lucide-react";
import { Song } from "@/types/Song";
import { useNavigate } from "react-router-dom";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { useSongs } from "@/hooks/api/useSongs";
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
  const { useDeleteSong } = useSongs();
  const deleteSongMutation = useDeleteSong();
  const [isAddingToQueue, setIsAddingToQueue] = useState(false);

  const handlePlayNow = () => {
    onClose(); // Close dialog first
    navigate(`/player/${song.id}`); // Navigate to player
  };

  const handleAddToQueue = async () => {
    if (song.status !== "processed") {
      toast.error("Song is not ready for playback yet");
      return;
    }

    setIsAddingToQueue(true);
    try {
      await addToQueueMutation.mutateAsync({
        songId: song.id,
        singer: "Unknown Singer", // TODO: Get from user preferences or input
      });
      toast.success(`"${song.title}" added to queue`);
    } catch (error) {
      console.error("Failed to add song to queue:", error);
      toast.error("Failed to add song to queue");
    } finally {
      setIsAddingToQueue(false);
    }
  };

  const isProcessed = song.status === "processed";

  return (
    <div className="border-t pt-6 mt-6">
      <div className="flex gap-3 flex-col sm:flex-row">
        <Button
          onClick={handlePlayNow}
          disabled={!isProcessed}
          className="flex-1 sm:max-w-[200px] flex items-center gap-2"
          size="lg"
        >
          <Play size={16} />
          Play Now
        </Button>

        <Button
          variant="outline"
          onClick={handleAddToQueue}
          disabled={!isProcessed || isAddingToQueue}
          className="flex-1 sm:max-w-[160px] flex items-center gap-2"
          size="lg"
        >
          <PlusCircle size={16} />
          {isAddingToQueue ? "Adding..." : "Add to Queue"}
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
    </div>
  );
};
