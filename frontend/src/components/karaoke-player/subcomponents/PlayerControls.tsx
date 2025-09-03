/**
 * PlayerControls - Play/pause, volume, and fullscreen controls
 * Configurable controls with accessibility features and keyboard support
 */

import React, { memo } from 'react';
import {
  Play,
  Pause,
  Minimize,
  Maximize,
  Volume1,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import type { PlayerControl } from '../KaraokePlayer.types';

interface PlayerControlsProps {
  // Player state
  isPlaying: boolean;
  isReady: boolean;
  vocalVolume: number;
  
  // UI state
  isFullscreen: boolean;
  showVolumeSlider: boolean;
  
  // Controls configuration
  controls?: PlayerControl[];
  
  // Event handlers
  onPlayPause: () => void;
  onVolumeChange: (volume: number) => void;
  onVolumeToggle: () => void;
  onFullscreenToggle: () => void;
  onVolumeSliderShow: (show: boolean) => void;
  
  className?: string;
}

const PlayerControls: React.FC<PlayerControlsProps> = memo(({
  isPlaying,
  isReady,
  vocalVolume,
  isFullscreen,
  showVolumeSlider,
  controls = ['play', 'volume', 'fullscreen'],
  onPlayPause,
  onVolumeChange,
  onVolumeToggle,
  onFullscreenToggle,
  onVolumeSliderShow,
  className = "",
}) => {
  const showPlay = controls.includes('play');
  const showVolume = controls.includes('volume');
  const showFullscreen = controls.includes('fullscreen');

  return (
    <div className={`flex items-center ${className}`} role="toolbar" aria-label="Player controls">
      {/* Play/Pause Button */}
      {showPlay && (
        <Button
          variant="ghost"
          aria-label={isPlaying ? "Pause" : "Play"}
          onClick={onPlayPause}
          disabled={!isReady}
          className="px-4"
          tabIndex={0}
        >
          {isPlaying ? <Pause size={48} aria-hidden="true" /> : <Play size={48} aria-hidden="true" />}
        </Button>
      )}

      {/* Volume Control */}
      {showVolume && (
        <div
          className="relative"
          onMouseEnter={() => onVolumeSliderShow(true)}
          onMouseLeave={() => onVolumeSliderShow(false)}
        >
          <Button
            variant="ghost"
            aria-label={vocalVolume === 0 ? "Unmute vocals" : "Mute vocals"}
            className="px-4"
            onClick={onVolumeToggle}
            tabIndex={0}
          >
            {vocalVolume === 0 ? (
              <VolumeX size={28} aria-hidden="true" />
            ) : vocalVolume < 0.5 ? (
              <Volume1 size={28} aria-hidden="true" />
            ) : (
              <Volume2 size={28} aria-hidden="true" />
            )}
          </Button>
          {showVolumeSlider && (
            <div 
              className="absolute bottom-full left-1/2 transform -translate-x-1/2 bg-primary rounded-md px-4 py-2 z-50 flex flex-col items-center"
              role="region"
              aria-label="Volume control"
            >
              <Slider
                orientation="vertical"
                min={0}
                max={1}
                step={0.01}
                value={[vocalVolume]}
                onValueChange={([val]) => onVolumeChange(val)}
                aria-label="Vocals volume"
                className="h-24 w-4"
              />
            </div>
          )}
        </div>
      )}

      {/* Fullscreen Button */}
      {showFullscreen && (
        <Button
          variant="ghost"
          aria-label={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          onClick={onFullscreenToggle}
          className="px-4"
          tabIndex={0}
        >
          {isFullscreen ? (
            <Minimize size={24} aria-hidden="true" />
          ) : (
            <Maximize size={24} aria-hidden="true" />
          )}
        </Button>
      )}
    </div>
  );
});

PlayerControls.displayName = 'PlayerControls';

export default PlayerControls;