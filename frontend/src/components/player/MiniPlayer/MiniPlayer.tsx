/**
 * MiniPlayer - Floating mini-player component
 * 
 * A persistent UI element that appears when navigating away from the player page
 * while a song is playing. Renders at the app root level using React Portal.
 */

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Music } from 'lucide-react';
import { useMiniPlayer } from './useMiniPlayer';
import MiniPlayerControls from './MiniPlayerControls';
import MiniPlayerProgress from './MiniPlayerProgress';
import { formatTime } from '@/utils/formatters';
import type { MiniPlayerProps } from './MiniPlayer.types';

const MiniPlayer: React.FC<MiniPlayerProps> = ({ className = '' }) => {
  const {
    shouldShow,
    songTitle,
    songArtist,
    isPlaying,
    currentTime,
    duration,
    position,
    handlePlayPause,
    handleExpand,
    handleClose,
  } = useMiniPlayer();

  // Animation state for smooth entrance/exit
  const [isVisible, setIsVisible] = useState(false);
  const [shouldRender, setShouldRender] = useState(false);

  // Handle animation timing
  useEffect(() => {
    if (shouldShow) {
      setShouldRender(true);
      // Small delay to trigger CSS transition
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setIsVisible(true);
        });
      });
    } else {
      setIsVisible(false);
      // Wait for exit animation to complete
      const timer = setTimeout(() => {
        setShouldRender(false);
      }, 300); // Match CSS transition duration
      return () => clearTimeout(timer);
    }
  }, [shouldShow]);

  // Don't render if not needed
  if (!shouldRender) return null;

  const miniPlayerContent = (
    <div
      className={`fixed z-50 shadow-2xl rounded-lg overflow-hidden bg-gradient-to-br from-gray-900 to-gray-950 border border-white/10 transition-all duration-300 ease-out ${className}`}
      style={{
        bottom: position.y,
        right: position.x,
        width: '320px',
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.95)',
      }}
      role="region"
      aria-label="Mini player"
    >
      {/* Main content area */}
      <div className="relative">
        {/* Background gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent pointer-events-none" />

        {/* Content */}
        <div className="relative p-3">
          {/* Song info and icon */}
          <div className="flex items-center gap-3 mb-2">
            {/* Music icon / album art placeholder */}
            <div className="flex-shrink-0 w-10 h-10 rounded bg-gradient-to-br from-dark-cyan/30 to-orange-peel/30 flex items-center justify-center">
              <Music size={20} className="text-orange-peel" />
            </div>

            {/* Song title and artist */}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-white truncate">
                {songTitle || 'Unknown Title'}
              </div>
              <div className="text-xs text-white/60 truncate">
                {songArtist || 'Unknown Artist'}
              </div>
            </div>
          </div>

          {/* Progress info */}
          <div className="flex items-center justify-between text-xs text-white/50 mb-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>

          {/* Progress bar */}
          <MiniPlayerProgress
            currentTime={currentTime}
            duration={duration}
            className="mb-2"
          />

          {/* Controls */}
          <MiniPlayerControls
            isPlaying={isPlaying}
            onPlayPause={handlePlayPause}
            onExpand={handleExpand}
            onClose={handleClose}
          />
        </div>
      </div>
    </div>
  );

  // Render using portal to document body
  return createPortal(miniPlayerContent, document.body);
};

export default MiniPlayer;
