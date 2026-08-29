/**
 * PerformanceControlsPanel - the performer's phone.
 *
 * Renders the very same ControlsStrip the stage's left rail does, at touch
 * density, so the two surfaces cannot drift apart again. Transport and the
 * stage-fullscreen button sit underneath.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Maximize, Pause, Play, SkipBack } from "lucide-react";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { formatTime } from "@/utils/formatters";
import ControlsStrip from "../controls/ControlsStrip";

const PerformanceControlsPanel: React.FC = () => {
  const {
    isPlaying,
    isReady,
    currentTime,
    duration,
    userPlay,
    userPause,
    seek,
  } = useKaraokePlayerStore();

  return (
    <div className="flex h-full flex-col gap-2.5 overflow-hidden p-1">
      <ControlsStrip density="touch" className="flex-1" />

      <div className="flex shrink-0 flex-col gap-2.5 pt-0.5">
        <div className="flex items-center gap-3">
          <span className="font-accent text-[22px] leading-none text-foreground/70">
            {formatTime(currentTime)}
          </span>
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={seek}
            className="flex-1"
          />
          <span className="font-accent text-[22px] leading-none text-foreground/70">
            {formatTime(duration)}
          </span>
        </div>

        <div className="flex items-center justify-center gap-7">
          <Button
            variant="ghost"
            size="icon"
            className="size-12 text-foreground/70"
            disabled={!isReady}
            onClick={() => seek(0)}
            aria-label="Restart song"
          >
            <SkipBack className="size-6" fill="currentColor" />
          </Button>

          <Button
            className="size-16 rounded-full bg-primary text-card-foreground shadow-glow-primary hover:bg-primary/90"
            disabled={!isReady}
            onClick={isPlaying ? userPause : userPlay}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <Pause className="size-7.5" fill="currentColor" />
            ) : (
              <Play className="size-7.5" fill="currentColor" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="size-12 text-foreground/70"
            onClick={() => sessionWebSocketService.toggleFullscreen()}
            aria-label="Toggle fullscreen on stage"
          >
            <Maximize className="size-6" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default PerformanceControlsPanel;
