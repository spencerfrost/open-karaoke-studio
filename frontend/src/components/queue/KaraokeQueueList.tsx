import React from "react";
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
        <p>Add songs to get started!</p>
      </div>
    );
  }

  // TODO: add drag-and-drop functionality for reordering

  items = items.filter((item) => item.position !== 0);

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
