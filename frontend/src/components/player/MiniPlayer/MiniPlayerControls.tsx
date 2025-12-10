/**
 * MiniPlayerControls - Play/pause, expand, and close buttons
 */

import React from 'react';
import { Play, Pause, Maximize2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MiniPlayerControlsProps {
  isPlaying: boolean;
  onPlayPause: () => void;
  onExpand: () => void;
  onClose: () => void;
  className?: string;
}

const MiniPlayerControls: React.FC<MiniPlayerControlsProps> = ({
  isPlaying,
  onPlayPause,
  onExpand,
  onClose,
  className = '',
}) => {
  return (
    <div className={`flex items-center justify-between gap-2 ${className}`}>
      {/* Play/Pause Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onPlayPause}
        className="h-8 w-8 text-white hover:bg-white/20 hover:text-white"
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? (
          <Pause size={18} aria-hidden="true" />
        ) : (
          <Play size={18} aria-hidden="true" />
        )}
      </Button>

      <div className="flex items-center gap-1">
        {/* Expand to Full Player */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onExpand}
          className="h-8 w-8 text-white hover:bg-white/20 hover:text-white"
          aria-label="Expand to full player"
        >
          <Maximize2 size={16} aria-hidden="true" />
        </Button>

        {/* Close/Dismiss Mini-Player */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-8 w-8 text-white hover:bg-white/20 hover:text-white"
          aria-label="Close mini-player"
        >
          <X size={16} aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
};

export default MiniPlayerControls;
