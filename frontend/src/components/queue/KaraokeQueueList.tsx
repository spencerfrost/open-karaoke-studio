import React from "react";
import { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";
import KaraokeQueueItem from "./KaraokeQueueItem";
import vintageTheme from "@/utils/theme";

interface KaraokeQueueListProps {
  items: KaraokeQueueItemWithSong[];
  currentSongId?: string | null;
  onRemove?: (id: string) => void;
  emptyMessage?: string;
  className?: string;
}

const KaraokeQueueList: React.FC<KaraokeQueueListProps> = ({
  items,
  currentSongId = null,
  onRemove,
  emptyMessage = "No songs in the queue",
  className = "",
}) => {
  const colors = vintageTheme.colors;

  if (!items.length) {
    return (
      <div
        className={`p-8 text-center ${className}`}
        style={{ color: `${colors.lemonChiffon}80` }}
      >
        <p className="text-lg mb-3">{emptyMessage}</p>
        <p>Add songs to get started!</p>
      </div>
    );
  }

  // For a real implementation, you would add drag-and-drop functionality
  // using a library like react-beautiful-dnd for reordering

  return (
    <div className={className}>
      {items.map((item, index) => (
        <KaraokeQueueItem
          key={item.id}
          item={item}
          index={index}
          isActive={item.id === currentSongId}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
};

export default KaraokeQueueList;
