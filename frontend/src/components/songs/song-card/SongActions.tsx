import React from "react";
import { Button } from "@/components/ui/button";
import { ListPlus, Trash, MoreVertical } from "lucide-react";
import { SongActionsProps } from "./SongCard.types";

export const SongActions: React.FC<SongActionsProps> = ({
  onQueue,
  onDelete,
  onDetails,
}) => {
  return (
    <div className="flex items-center justify-around">
      <Button
        variant="ghost"
        size="lg"
        className="text-accent p-0 w-12 h-12"
        aria-label="Add to karaoke queue"
        onClick={onQueue}
      >
        <ListPlus className="size-6" />
      </Button>

      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className="text-destructive bg-background/80 backdrop-blur-sm w-12 h-12 p-0"
          aria-label="Delete song"
          onClick={onDelete}
        >
          <Trash className="size-6" />
        </Button>
      )}

      {onDetails && (
        <Button
          variant="ghost"
          size="icon"
          className="text-foreground bg-background/80 backdrop-blur-sm w-12 h-12 p-0"
          aria-label="Song details"
          onClick={onDetails}
        >
          <MoreVertical className="size-6" />
        </Button>
      )}
    </div>
  );
};
