import React from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { Button } from "@/components/ui/button";
import { Volume2, Play, Pause, Mic } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import LyricsTimingControls from "@/features/lyrics/components/LyricsTimingControls";
import LyricsSizeControl from "@/features/lyrics/components/LyricsSizeControl";
import { useSessionStore } from "@/stores/sessionStore";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";

const PerformanceControlsPanel: React.FC = () => {
  const { isPlaying, currentTime, duration, userPlay, userPause, seek } =
    useKaraokePlayerStore();

  const { vocalVolume, toggleVocalsVolume } = usePerformanceControlsLogic();

  const { sessionId, displayCode, isHost } = useSessionStore();

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-hidden">
      {/* Play/Pause + Progress Bar - Inline */}
      <div className="flex items-center gap-3 border-b border-orange-peel/30 pb-3">
        <Button
          className="rounded-full h-20 w-20 shrink-0 bg-gradient-to-br from-orange-peel to-rust hover:from-orange-peel/90 hover:to-rust/90 shadow-lg transition-all hover:scale-105"
          onClick={isPlaying ? userPause : userPlay}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause size={40} /> : <Play size={40} />}
        </Button>
        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
          className="flex-1"
        />
      </div>

      <div className="flex-1 grid grid-cols-2">
        <div className="flex flex-col items-stretch gap-4 justify-between border-r border-orange-peel/30 pr-4">
          {sessionId && displayCode && (
            <div className="text-sm text-center">
              <SessionInfoDisplay
                variant="code"
                trigger="click"
                visibility="all"
              />
            </div>
          )}
          <LyricsSizeControl />
          <LyricsTimingControls />
        </div>
        {/* Vocals Volume Control */}
        <div className="flex flex-col items-center gap-3 pl-4">
          <div className="flex items-center gap-2">
            <Mic className="text-primary" size={24} />
            <span className="text-lg font-semibold text-lemon-chiffon">
              Volume: {Math.round(vocalVolume * 100)}%
            </span>
          </div>

          <div className="flex flex-col items-center gap-3 flex-1 w-full max-w-xs">
            <Slider
              value={[vocalVolume]}
              min={0}
              max={1}
              step={0.05}
              variant="performance-hero"
              orientation="vertical"
              onValueChange={([v]) =>
                useKaraokePlayerStore.getState().setVocalVolume(v)
              }
              className="flex-1 h-full"
            />
            <Button
              variant="outline"
              size="lg"
              onClick={toggleVocalsVolume}
              className="w-full max-w-[180px]"
            >
              <Volume2 size={20} className="mr-2" />
              {vocalVolume === 0 ? "Unmute" : "Mute"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceControlsPanel;
