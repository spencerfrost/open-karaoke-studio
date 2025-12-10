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
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import type { PlayerControl } from '../../types/KaraokePlayer.types';

interface PlayerControlsProps {
  // Player state
  isPlaying: boolean;
  isReady: boolean;
  vocalVolume: number;
  songEnded?: boolean; // True when song finished naturally
  
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
  songEnded = false,
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

  // Determine play button icon and label
  const getPlayButtonProps = () => {
    if (isPlaying) {
      return {
        icon: <Pause size={48} aria-hidden="true" />,
        label: "Pause"
      };
    }
    if (songEnded) {
      return {
        icon: <RotateCcw size={48} aria-hidden="true" />,
        label: "Replay from beginning"
      };
    }
    return {
      icon: <Play size={48} aria-hidden="true" />,
      label: "Play"
    };
  };

  const playButtonProps = getPlayButtonProps();

  return (
    <div className={`flex items-center ${className}`} role="toolbar" aria-label="Player controls">
      {/* Play/Pause/Replay Button */}
      {showPlay && (
        <Button
          variant="ghost"
          aria-label={playButtonProps.label}
          onClick={onPlayPause}
          disabled={!isReady}
          className="px-4"
          tabIndex={0}
        >
          {playButtonProps.icon}
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