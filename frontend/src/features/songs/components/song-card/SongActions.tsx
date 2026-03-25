import React from "react";
import { Button } from "@/components/ui/button";
import { ListPlus, Trash, MoreVertical } from "lucide-react";
import { SongActionsProps } from "./SongCard.types";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";

export const SongActions: React.FC<SongActionsProps> = ({
  song,
  onQueue,
  onDelete,
  onDetails,
}) => {
  const isProcessing = useProcessingIndicators((state) =>
    state.isProcessing(song.id),
  );
  return (
    <div className="flex items-center justify-around">
      <Button
        variant="ghost"
        size="icon"
        className="text-accent size-7"
        aria-label="Add to karaoke queue"
        onClick={onQueue}
        disabled={isProcessing}
      >
        <ListPlus className="size-5" />
      </Button>

      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive p-2 size-6"
          aria-label="Delete song"
          onClick={onDelete}
          disabled={isProcessing}
        >
          <Trash className="size-5" />
        </Button>
      )}

      {onDetails && (
        <Button
          variant="ghost"
          size="icon"
          className="text-foreground p-2 size-6"
          aria-label="Song details"
          onClick={onDetails}
          disabled={isProcessing}
        >
          <MoreVertical className="size-5" />
        </Button>
      )}
    </div>
  );
};
