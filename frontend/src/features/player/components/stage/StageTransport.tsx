/**
 * StageTransport - the stage's transport, under the centre column only so the
 * rails keep full viewport height.
 *
 * Reads playback straight from the player store — the same source the phone's
 * transport uses — so both surfaces stay in step without extra plumbing.
 */

import React from "react";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { formatTime } from "@/utils/formatters";
import ProgressBar from "../subcomponents/ProgressBar";

interface StageTransportProps {
  /** Play the next queue item; omitted when the queue has nothing after this. */
  onNext?: () => void;
}

const StageTransport: React.FC<StageTransportProps> = ({ onNext }) => {
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
    <div className="flex w-full shrink-0 flex-col gap-4.5 pt-5">
      <div className="flex items-center gap-6">
        <span className="w-21 font-accent text-[32px] leading-none text-foreground/70">
          {formatTime(currentTime)}
        </span>
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
          className="flex-1"
        />
        <span className="w-21 text-right font-accent text-[32px] leading-none text-foreground/70">
          {formatTime(duration)}
        </span>
      </div>

      <div className="flex items-center justify-center gap-10">
        <Button
          variant="ghost"
          size="icon"
          className="size-16 text-foreground/70 hover:text-foreground"
          disabled={!isReady}
          onClick={() => seek(0)}
          aria-label="Restart song"
        >
          <SkipBack className="size-8.5" fill="currentColor" />
        </Button>

        <Button
          className="size-22 rounded-full bg-primary text-card-foreground shadow-glow-primary hover:bg-primary/90"
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
          className="size-16 text-foreground/70 hover:text-foreground"
          disabled={!onNext}
          onClick={onNext}
          aria-label="Play next song"
        >
          <SkipForward className="size-8.5" fill="currentColor" />
        </Button>
      </div>
    </div>
  );
};

export default StageTransport;
