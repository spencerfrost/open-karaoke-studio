import React from "react";
import { Music, X } from "lucide-react";
import { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

interface KaraokeQueueItemProps {
  item: KaraokeQueueItemWithSong;
  index: number;
  isActive?: boolean;
  onRemove?: (id: string) => void;
  className?: string;
}

const KaraokeQueueItem: React.FC<KaraokeQueueItemProps> = ({
  item,
  index,
  isActive = false,
  onRemove,
  className = "",
}) => {
  return (
    <div
      className={`p-4 flex items-center border-b border-orange-peel/30 ${className} ${
        isActive ? 'bg-dark-cyan/30' : 'bg-transparent'
      }`}
    >
      {/* Position indicator */}
      <div
        className={`h-10 w-10 rounded-full flex items-center justify-center mr-4 text-lg font-semibold shrink-0 ${
          isActive 
            ? 'bg-dark-cyan text-lemon-chiffon' 
            : 'bg-orange-peel/25 text-orange-peel'
        }`}
      >
        {index + 1}
      </div>

      {/* Song info */}
      <div className="flex-1 min-w-0">
        <h3
          className={`font-semibold text-xl truncate ${
            isActive ? 'text-orange-peel' : 'text-lemon-chiffon'
          }`}
        >
          {item.song.title}
        </h3>
        <p className="opacity-80 truncate">
          {item.song.artist} •{" "}
          <span className="text-orange-peel">
            Singer: {item.singer}
          </span>
        </p>
      </div>

      {/* Album art / icon */}
      <div className="h-12 w-12 rounded-md flex items-center justify-center ml-3 mr-1 shrink-0 bg-orange-peel/20">
        {item.song.coverArt ? (
          <img
            src={item.song.coverArt}
            alt={item.song.title}
            className="h-full w-full object-cover rounded-md"
          />
        ) : (
          <Music size={24} className="text-dark-cyan" />
        )}
      </div>

      {/* Remove button */}
      {onRemove && (
        <button
          className="p-2 ml-1 rounded-full hover:bg-black hover:bg-opacity-20 transition-colors shrink-0"
          onClick={() => onRemove(item.id)}
          aria-label="Remove from queue"
        >
          <X
            size={18}
            className={isActive ? 'text-orange-peel' : 'text-lemon-chiffon'}
          />
        </button>
      )}
    </div>
  );
};

export default KaraokeQueueItem;
