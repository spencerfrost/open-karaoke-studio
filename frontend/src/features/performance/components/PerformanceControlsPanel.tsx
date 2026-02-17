import React, { useState } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Volume2,
  VolumeX,
  Play,
  Pause,
  Maximize,
  Settings,
  Timer,
  Mic,
  Music,
} from "lucide-react";
import { Slider } from "@/components/ui/slider";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import LyricsTimingControls from "@/features/lyrics/components/LyricsTimingControls";
import LyricsSizeControl from "@/features/lyrics/components/LyricsSizeControl";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { useSessionStore } from "@/stores/sessionStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";

const PerformanceControlsPanel: React.FC = () => {
  const {
    isPlaying,
    currentTime,
    duration,
    userPlay,
    userPause,
    seek,
    instrumentalVolume,
    setInstrumentalVolume,
    playbackSpeed,
    setPlaybackSpeed,
  } = useKaraokePlayerStore();

  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();

  const { sessionId, displayCode } = useSessionStore();

  const [timingSheetOpen, setTimingSheetOpen] = useState(false);
  const [moreOptionsSheetOpen, setMoreOptionsSheetOpen] = useState(false);

  return (
    <div className="h-full flex flex-col p-4 gap-3 overflow-hidden">
      {/* Main controls area */}
      <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
        {/* Left: Primary vocals (hero) */}
        <div className="flex flex-col items-center gap-2 border-r border-orange-peel/30 pr-4 min-h-0">
          <div className="flex items-center gap-2">
            <Mic className="text-primary shrink-0" size={18} />
            <span className="text-sm font-semibold text-lemon-chiffon">
              Vocals {Math.round(vocalVolume * 100)}%
            </span>
          </div>
          <div className="flex-1 min-h-0 w-full flex flex-col items-center gap-2">
            <Slider
              value={[vocalVolume]}
              min={0}
              max={1}
              step={0.05}
              variant="performance-hero"
              orientation="vertical"
              onValueChange={([v]) => setVocalVolume(v)}
              className="flex-1 min-h-0"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={toggleVocalsVolume}
              className="w-full"
            >
              {vocalVolume === 0 ? (
                <>
                  <VolumeX size={16} className="mr-1" />
                  Unmute
                </>
              ) : (
                <>
                  <Volume2 size={16} className="mr-1" />
                  Mute
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Right: Secondary controls */}
        <div className="flex flex-col gap-3 pl-4 min-h-0 overflow-y-auto">
          {/* Backing vocals (smaller slider) */}
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center gap-1">
              <Music className="text-muted-foreground shrink-0" size={14} />
              <span className="text-xs text-lemon-chiffon/80">
                Backing {Math.round(backingVocalVolume * 100)}%
              </span>
            </div>
            <Slider
              value={[backingVocalVolume]}
              min={0}
              max={1}
              step={0.05}
              variant="performance"
              orientation="vertical"
              onValueChange={([v]) => setBackingVocalVolume(v)}
              className="h-20"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={toggleBackingVocalsVolume}
              className="w-full text-xs"
            >
              {backingVocalVolume === 0 ? (
                <>
                  <VolumeX size={14} className="mr-1" />
                  Unmute
                </>
              ) : (
                <>
                  <Volume2 size={14} className="mr-1" />
                  Mute
                </>
              )}
            </Button>
          </div>

          <div className="border-t border-orange-peel/20" />

          {/* Lyrics size */}
          <LyricsSizeControl />

          <div className="border-t border-orange-peel/20" />

          {/* Fix Lyrics Timing */}
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => setTimingSheetOpen(true)}
          >
            <Timer size={14} className="mr-2" />
            Fix Lyrics Timing
          </Button>

          {/* More Options */}
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => setMoreOptionsSheetOpen(true)}
          >
            <Settings size={14} className="mr-2" />
            More Options
          </Button>
        </div>
      </div>

      {/* Transport bar — pinned to bottom */}
      <div className="border-t border-orange-peel/30 pt-3 flex flex-col gap-2 shrink-0">
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
          className="w-full"
        />
        <div className="flex items-center justify-between">
          <Button
            className="rounded-full h-14 w-14 bg-gradient-to-br from-orange-peel to-rust hover:from-orange-peel/90 hover:to-rust/90 shadow-lg transition-all hover:scale-105"
            onClick={isPlaying ? userPause : userPlay}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause size={28} /> : <Play size={28} />}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 text-lemon-chiffon/70 hover:text-lemon-chiffon"
            onClick={() => sessionWebSocketService.toggleFullscreen()}
            aria-label="Toggle fullscreen on stage"
          >
            <Maximize size={22} />
          </Button>
        </div>
      </div>

      {/* Fix Lyrics Timing Sheet */}
      <Sheet open={timingSheetOpen} onOpenChange={setTimingSheetOpen}>
        <SheetContent side="bottom" className="pb-8">
          <SheetHeader>
            <SheetTitle>Fix Lyrics Timing</SheetTitle>
          </SheetHeader>
          <div className="pt-4">
            <LyricsTimingControls />
          </div>
        </SheetContent>
      </Sheet>

      {/* More Options Sheet */}
      <Sheet open={moreOptionsSheetOpen} onOpenChange={setMoreOptionsSheetOpen}>
        <SheetContent side="bottom" className="pb-8">
          <SheetHeader>
            <SheetTitle>More Options</SheetTitle>
          </SheetHeader>
          <div className="pt-4 flex flex-col gap-5">
            {/* Instrumental volume */}
            <div className="flex flex-col gap-2">
              <span className="text-xs text-lemon-chiffon/80">
                Instrumental Volume {Math.round(instrumentalVolume * 100)}%
              </span>
              <Slider
                value={[instrumentalVolume]}
                min={0}
                max={1}
                step={0.05}
                variant="performance"
                orientation="horizontal"
                onValueChange={([v]) => setInstrumentalVolume(v)}
              />
            </div>

            {/* Playback speed */}
            <div className="flex flex-col gap-2">
              <span className="text-xs text-lemon-chiffon/80">
                Playback Speed {playbackSpeed.toFixed(2)}x
              </span>
              <Slider
                value={[playbackSpeed]}
                min={0.5}
                max={1.5}
                step={0.05}
                variant="performance"
                orientation="horizontal"
                onValueChange={([v]) => setPlaybackSpeed(v)}
              />
              <Button
                variant="outline"
                size="sm"
                className="w-fit self-end text-xs"
                onClick={() => setPlaybackSpeed(1)}
              >
                Reset to 1×
              </Button>
            </div>

            {/* Session info */}
            {sessionId && displayCode && (
              <div className="border-t border-orange-peel/20 pt-4">
                <span className="text-xs text-lemon-chiffon/80 block mb-2">
                  Session
                </span>
                <SessionInfoDisplay
                  variant="code"
                  trigger="click"
                  visibility="all"
                />
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default PerformanceControlsPanel;
