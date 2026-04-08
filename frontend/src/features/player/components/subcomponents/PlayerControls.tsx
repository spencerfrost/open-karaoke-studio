/**
 * PlayerControls - Play/pause, volume, and fullscreen controls
 * Configurable controls with accessibility features and keyboard support
 */

import React, { memo, useState, useRef } from "react";
import {
  Play,
  Pause,
  Minimize,
  Maximize,
  Volume1,
  Volume2,
  VolumeX,
  RotateCcw,
  SkipForward,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { SettingsMenu } from "./SettingsMenu";
import type { PlayerControl } from "../../types/KaraokePlayer.types";

interface PlayerControlsProps {
  // Player state
  isPlaying: boolean;
  isReady: boolean;
  vocalVolume: number;
  songEnded?: boolean; // True when song finished naturally
  hasNextSong?: boolean; // True when queue has a next song
  // UI state
  isFullscreen: boolean;

  // Controls configuration
  controls?: PlayerControl[];

  // Event handlers
  onPlayPause: () => void;
  onVolumeChange: (volume: number) => void;
  onVolumeToggle: () => void;
  onFullscreenToggle: () => void;

  className?: string;
}

const PlayerControls: React.FC<PlayerControlsProps> = memo(
  ({
    isPlaying,
    isReady,
    vocalVolume,
    songEnded = false,
    hasNextSong = false,
    isFullscreen,
    onPlayPause,
    onVolumeChange,
    onVolumeToggle,
    onFullscreenToggle,
    className = "",
  }) => {
    const [showVolumeSlider, setShowVolumeSlider] = useState(false);
    const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const handleMouseEnter = () => {
      setShowVolumeSlider(true);
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
        closeTimeoutRef.current = null;
      }
    };

    const handleMouseLeave = () => {
      closeTimeoutRef.current = setTimeout(() => {
        setShowVolumeSlider(false);
      }, 200);
    };
    // Determine play button icon and label
    const getPlayButtonProps = () => {
      if (isPlaying) {
        return {
          icon: <Pause size={48} aria-hidden="true" />,
          label: "Pause",
        };
      }
      if (songEnded) {
        if (hasNextSong) {
          return {
            icon: <SkipForward size={48} aria-hidden="true" />,
            label: "Play next",
          };
        }
        return {
          icon: <RotateCcw size={48} aria-hidden="true" />,
          label: "Replay from beginning",
        };
      }
      return {
        icon: <Play size={48} aria-hidden="true" />,
        label: "Play",
      };
    };

    const playButtonProps = getPlayButtonProps();

    return (
      <div
        className={`w-full grid grid-cols-3 py-6 ${className}`}
        role="toolbar"
        aria-label="Player controls"
      >
        {/* Volume Control */}
        <div
          className="relative justify-self-start flex items-center"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Button
            variant="pill"
            aria-label={vocalVolume === 0 ? "Unmute vocals" : "Mute vocals"}
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
              className="absolute left-full top-1/2 transform -translate-y-1/2 ml-2 bg-transparent z-50"
              role="region"
              aria-label="Volume control"
            >
              <div
                className="p-3"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
              >
                <Slider
                  min={0}
                  max={1}
                  step={0.01}
                  value={[vocalVolume]}
                  onValueChange={([val]) => onVolumeChange(val)}
                  aria-label="Vocals volume"
                  className="w-24 h-4"
                />
              </div>
            </div>
          )}
        </div>

        {/* Play/Pause/Replay Button */}
        <Button
          aria-label={playButtonProps.label}
          onClick={onPlayPause}
          disabled={!isReady}
          className="p-4 justify-self-center rounded-full"
          variant="pill"
          size="lg"
          tabIndex={0}
        >
          {playButtonProps.icon}
        </Button>

        {/* Right Controls Group - Speed, Tap Tempo, and Fullscreen */}
        <div className="flex items-center gap-2 justify-self-end">
          {/* Settings Menu */}
          <SettingsMenu />

          {/* Fullscreen Button */}
          <Button
            variant="pill"
            aria-label={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
            onClick={onFullscreenToggle}
            tabIndex={0}
          >
            {isFullscreen ? (
              <Minimize size={24} aria-hidden="true" />
            ) : (
              <Maximize size={24} aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>
    );
  },
);

PlayerControls.displayName = "PlayerControls";

export default PlayerControls;
