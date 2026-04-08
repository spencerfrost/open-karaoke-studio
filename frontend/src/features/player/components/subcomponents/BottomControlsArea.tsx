/**
 * BottomControlsArea - Mouse-aware bottom controls for karaoke player
 * Toggles between interactive (floating hero button) and minimal (visualizer) states
 */

import React from "react";
import PlayerControls from "./PlayerControls";
import ProgressBar from "./ProgressBar";
import AudioVisualizer from "./AudioVisualizer";
import { IndeterminateProgress } from "@/components/ui/indeterminate-progress";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";

interface BottomControlsAreaProps {
  // Player state
  song: Song | null;
  isLoading: boolean;
  isReady: boolean;
  isPlaying: boolean;
  songEnded: boolean;
  currentTime: number;
  duration: number;
  vocalVolume: number;
  isFullscreen: boolean;

  // Configuration
  hasNextSong?: boolean;
  mouseRecentlyMoved: boolean;

  // Callbacks
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onVolumeToggle: () => void;
  onFullscreenToggle: () => void;
}
const BottomControlsArea: React.FC<BottomControlsAreaProps> = ({
  song,
  isLoading,
  isReady,
  isPlaying,
  songEnded,
  currentTime,
  duration,
  vocalVolume,
  isFullscreen,
  hasNextSong = false,
  mouseRecentlyMoved,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onVolumeToggle,
  onFullscreenToggle,
}) => {
  // Container classes
  const containerClass = cn(
    "w-full absolute bottom-0 left-0 right-0 z-20",
    "transition-all duration-300",
    (mouseRecentlyMoved || !isPlaying) && "px-12",
  );

  // Progress bar classes
  const progressClass =
    "transition-all duration-300 rounded-full mb-3 shadow-lg";

  return (
    <div className={containerClass}>
      {/* Audio Visualizer - Minimal State Only */}
      <div>
        {isPlaying && !mouseRecentlyMoved && (
          <AudioVisualizer className="w-full" />
        )}
      </div>

      {/* Progress Bar */}
      {song &&
        (isLoading ? (
          <IndeterminateProgress className={progressClass} size="sm" />
        ) : (
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={onSeek}
            className={progressClass}
          />
        ))}

      {/* Controls - Interactive State Only */}
      <div>
        {song && (!isPlaying || mouseRecentlyMoved) && (
          <div className="flex justify-center items-center">
            <PlayerControls
              isPlaying={isPlaying}
              isReady={isReady}
              vocalVolume={vocalVolume}
              songEnded={songEnded}
              hasNextSong={hasNextSong}
              isFullscreen={isFullscreen}
              onPlayPause={onPlayPause}
              onVolumeChange={onVolumeChange}
              onVolumeToggle={onVolumeToggle}
              onFullscreenToggle={onFullscreenToggle}
            />
          </div>
        )}
      </div>
    </div>
  );
};

BottomControlsArea.displayName = "BottomControlsArea";

export default BottomControlsArea;
