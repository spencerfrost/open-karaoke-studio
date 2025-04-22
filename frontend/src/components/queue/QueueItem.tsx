import React from 'react';
import { Music, X } from 'lucide-react';
import { QueueItemWithSong } from '../../types/Queue';
import vintageTheme from '../../utils/theme';

interface QueueItemProps {
  item: QueueItemWithSong;
  index: number;
  isActive?: boolean;
  onRemove?: (id: string) => void;
  className?: string;
}

const QueueItem: React.FC<QueueItemProps> = ({
  item,
  index,
  isActive = false,
  onRemove,
  className = '',
}) => {
  const colors = vintageTheme.colors;
  
  return (
    <div 
      className={`p-4 flex items-center ${className}`}
      style={{
        backgroundColor: isActive ? `${colors.darkCyan}30` : 'transparent',
        borderBottom: `1px solid ${colors.orangePeel}30`,
      }}
    >
      {/* Position indicator */}
      <div 
        className="h-10 w-10 rounded-full flex items-center justify-center mr-4 text-lg font-semibold shrink-0"
        style={{
          backgroundColor: isActive ? colors.darkCyan : `${colors.orangePeel}40`,
          color: isActive ? colors.lemonChiffon : colors.orangePeel,
        }}
      >
        {index + 1}
      </div>
      
      {/* Song info */}
      <div className="flex-1 min-w-0">
        <h3 
          className="font-semibold text-xl truncate"
          style={{
            color: isActive ? colors.orangePeel : colors.lemonChiffon,
          }}
        >
          {item.song.title}
        </h3>
        <p className="opacity-80 truncate">
          {item.song.artist} • <span style={{ color: colors.orangePeel }}>Singer: {item.singer}</span>
        </p>
      </div>
      
      {/* Album art / icon */}
      <div 
        className="h-12 w-12 rounded-md flex items-center justify-center ml-3 mr-1 shrink-0"
        style={{ backgroundColor: `${colors.orangePeel}20` }}
      >
        {item.song.coverArt ? (
          <img
            src={item.song.coverArt}
            alt={item.song.title}
            className="h-full w-full object-cover rounded-md"
          />
        ) : (
          <Music size={24} style={{ color: colors.darkCyan }} />
        )}
      </div>
      
      {/* Remove button */}
      {onRemove && (
        <button
          className="p-2 ml-1 rounded-full hover:bg-black hover:bg-opacity-20 transition-colors shrink-0"
          onClick={() => onRemove(item.id)}
          aria-label="Remove from queue"
        >
          <X size={18} style={{ color: isActive ? colors.orangePeel : colors.lemonChiffon }} />
        </button>
      )}
    </div>
  );
};

export default QueueItem;
