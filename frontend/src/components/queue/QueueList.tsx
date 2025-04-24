import React from "react";
import { QueueItemWithSong } from "../../types/Queue";
import QueueItem from "./QueueItem";
import vintageTheme from "../../utils/theme";

interface QueueListProps {
  items: QueueItemWithSong[];
  currentItemId?: string | null;
  onRemove?: (id: string) => void;
  onReorder?: (items: QueueItemWithSong[]) => void;
  emptyMessage?: string;
  className?: string;
}

const QueueList: React.FC<QueueListProps> = ({
  items,
  currentItemId = null,
  onRemove,
  onReorder,
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
        <QueueItem
          key={item.id}
          item={item}
          index={index}
          isActive={item.id === currentItemId}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
};

export default QueueList;
