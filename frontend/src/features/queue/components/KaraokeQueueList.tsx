import React from "react";
import { Link } from "react-router-dom";
import { Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";
import KaraokeQueueItem from "./KaraokeQueueItem";

interface KaraokeQueueListProps {
  items: KaraokeQueueItemWithSong[];
  currentSongId?: string | null;
  onRemove?: (id: string) => void;
  onPlay?: (id: string) => void;
  emptyMessage?: string;
  className?: string;
}

const KaraokeQueueList: React.FC<KaraokeQueueListProps> = ({
  items,
  currentSongId = null,
  onRemove,
  onPlay,
  emptyMessage = "No songs in the queue",
  className = "",
}) => {
  if (!items.length) {
    return (
      <div className={`p-8 text-center text-lemon-chiffon/80 ${className}`}>
        <p className="text-lg mb-3">{emptyMessage}</p>
        <p className="mb-4">Add songs to get started!</p>
        <div className="flex justify-center">
          <Button asChild variant="secondary" size="sm" className="gap-2">
            <Link to="/library">
              <Library className="w-4 h-4" />
              Browse library
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  // TODO: add drag-and-drop functionality for reordering

  return (
    <div className={`${className}`}>
      {items.map((item, index) => (
        <KaraokeQueueItem
          key={item.id}
          item={item}
          index={index}
          isActive={item.id === currentSongId}
          onRemove={onRemove}
          onPlay={onPlay}
        />
      ))}
    </div>
  );
};

export default KaraokeQueueList;
