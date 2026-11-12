/**
 * PerformanceControlsPanel - the singer's phone, held in one hand while the
 * other holds the mic.
 *
 * Priority sets the room each part gets: the two faders take all the
 * leftover height, lyrics timing comes next, and play/pause is small - the
 * stage starts songs by itself, so it is rarely touched. The one-time fixes
 * live in the More sheet, and the page drops the bottom nav for a Close in
 * the top bar. Nothing here appears or
 * disappears during a song, so the layout never shifts under a thumb.
 *
 * The stage rail lays out the same controls its own way (ControlsStrip); the
 * two share behaviour through the store and useLyricsFixes.
 *
 * Progress is display only: a stray touch must not jump the song for the
 * whole room. There is no fullscreen button either: requestFullscreen()
 * demands user activation the stage's tab doesn't have, so the stage owns it.
 */

import React, { useState } from "react";
import { MoreHorizontal, Pause, Play, RotateCcw } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { Button } from "@/components/ui/button";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { formatTime } from "@/utils/formatters";
import { useBackingTrackAvailable } from "../hooks/useBackingTrackAvailable";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import PhoneFader from "./phone/PhoneFader";
import PhoneLyricsTiming from "./phone/PhoneLyricsTiming";
import PhoneMoreSheet from "./phone/PhoneMoreSheet";
import PhoneTopBar from "./phone/PhoneTopBar";

/** The only part that re-renders as the song plays. */
const PhoneProgress: React.FC = () => {
  const currentTime = useKaraokePlayerStore((s) => s.currentTime);
  const duration = useKaraokePlayerStore((s) => s.duration);

  return (
    <div className="flex shrink-0 items-center gap-3 px-1 font-accent text-xl leading-none text-foreground-dim">
      <span>{formatTime(currentTime)}</span>
      <ProgressBar
        currentTime={currentTime}
        duration={duration}
        className="flex-1"
      />
      <span>{formatTime(duration)}</span>
    </div>
  );
};

const sideButtonClass =
  "h-11 gap-1.5 px-3 text-base font-semibold text-foreground-dim hover:text-foreground";

const PerformanceControlsPanel: React.FC = () => {
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
  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();
  const backingAvailable = useBackingTrackAvailable();
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    // min-h: on a phone too short for every part at its smallest, the page
    // scrolls rather than squeezing the faders to nothing.
    <div
      data-tour="performance-controls"
      className="flex h-full min-h-[32rem] flex-col gap-2.5"
    >
      <PhoneTopBar />

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-2.5">
        <PhoneFader
          label="Original singer"
          tourId="vocal-level"
          volume={vocalVolume}
          onVolumeChange={setVocalVolume}
          onToggleMute={toggleVocalsVolume}
        />
        <PhoneFader
          label="Backup singers"
          volume={backingVocalVolume}
          onVolumeChange={setBackingVocalVolume}
          onToggleMute={toggleBackingVocalsVolume}
          unavailableReason={
            backingAvailable
              ? undefined
              : "This song doesn't have a separate backup-singer track."
          }
        />
      </div>

      <PhoneLyricsTiming />
      <PhoneProgress />

      <div className="grid shrink-0 grid-cols-3 items-center justify-items-center">
        <Button
          variant="ghost"
          disabled={!isReady}
          onClick={() => seek(0)}
          className={sideButtonClass}
        >
          <RotateCcw className="size-5" />
          Restart
        </Button>

        <Button
          className="size-12 rounded-full bg-primary text-primary-foreground shadow-glow-primary hover:bg-primary/90"
          disabled={!isReady}
          onClick={isPlaying ? userPause : userPlay}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? (
            <Pause className="size-5.5" fill="currentColor" />
          ) : (
            <Play className="size-5.5" fill="currentColor" />
          )}
        </Button>

        <Button
          variant="ghost"
          onClick={() => setMoreOpen(true)}
          className={sideButtonClass}
        >
          <MoreHorizontal className="size-5" />
          More
        </Button>
      </div>

      <PhoneMoreSheet open={moreOpen} onOpenChange={setMoreOpen} />
    </div>
  );
};

export default PerformanceControlsPanel;
