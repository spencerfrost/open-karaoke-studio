/**
 * StageTransport - the stage's transport, under the centre column only so the
 * rails keep full viewport height.
 *
 * Reads playback straight from the player store — the same source the phone's
 * transport uses — so both surfaces stay in step without extra plumbing.
 */

import React from "react";
import {
  Maximize,
  Minimize,
  Pause,
  Play,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useShallow } from "zustand/react/shallow";
import { formatTime } from "@/utils/formatters";
import ProgressBar from "../subcomponents/ProgressBar";
import { useSongPosition } from "../../hooks";

interface StageTransportProps {
  /** Play the next queue item; omitted when the queue has nothing after this. */
  onNext?: () => void;
  onToggleFullscreen?: () => void;
  isFullscreen?: boolean;
}

const StageTransport: React.FC<StageTransportProps> = ({
  onNext,
  onToggleFullscreen,
  isFullscreen = false,
}) => {
  const { isPlaying, isReady, userPlay, userPause, seek } =
    useKaraokePlayerStore(
      useShallow((s) => ({
        isPlaying: s.isPlaying,
        isReady: s.isReady,
        userPlay: s.userPlay,
        userPause: s.userPause,
        seek: s.seek,
      })),
    );

  return (
    <div className="flex w-full shrink-0 flex-col gap-4.5 pt-5">
      <StageTimeline seek={seek} />

      <div className="flex items-center justify-between">
        {/* Balances the fullscreen button on the right so the transport
            buttons stay centered on the row. */}
        <div className="size-12 shrink-0" aria-hidden="true" />

        <div className="flex items-center gap-10">
          <Button
            variant="ghost"
            size="icon"
            className="size-16 text-foreground-dim hover:text-foreground"
            disabled={!isReady}
            onClick={() => seek(0)}
            aria-label="Restart song"
          >
            <SkipBack className="size-8.5" fill="currentColor" />
          </Button>

          <Button
            className="size-22 rounded-full bg-primary text-primary-foreground shadow-glow-primary hover:bg-primary/90"
            disabled={!isReady}
            onClick={isPlaying ? userPause : userPlay}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <Pause className="size-10.5" fill="currentColor" />
            ) : (
              <Play className="size-10.5" fill="currentColor" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="size-16 text-foreground-dim hover:text-foreground"
            disabled={!onNext}
            onClick={onNext}
            aria-label="Play next song"
          >
            <SkipForward className="size-8.5" fill="currentColor" />
          </Button>
        </div>

        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleFullscreen}
          aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          className="size-12 shrink-0 text-foreground-faint hover:text-foreground"
        >
          {isFullscreen ? (
            <Minimize className="size-6" />
          ) : (
            <Maximize className="size-6" />
          )}
        </Button>
      </div>
    </div>
  );
};

/**
 * The elapsed time and progress bar - the only part of the transport that
 * moves with the song, so the only part that re-renders with it.
 */
const StageTimeline: React.FC<{ seek: (timeSeconds: number) => void }> = ({
  seek,
}) => {
  // Quarter-second steps: the bar moves a few pixels a second, and the
  // clock only shows whole seconds.
  const currentTime = useSongPosition(0.25);
  const duration = useKaraokePlayerStore((s) => s.duration);

  return (
    <div className="flex items-center gap-6">
      <span className="w-21 font-accent text-[2rem] leading-none text-foreground-dim">
        {formatTime(currentTime)}
      </span>
      <ProgressBar
        currentTime={currentTime}
        duration={duration}
        onSeek={seek}
        className="flex-1"
      />
      <span className="w-21 text-right font-accent text-[2rem] leading-none text-foreground-dim">
        {formatTime(duration)}
      </span>
    </div>
  );
};

export default StageTransport;
