import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Timer, Settings, Mic, Music, Play, Pause, Maximize } from "lucide-react";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import LyricsTimingControls from "@/features/lyrics/components/LyricsTimingControls";
import LyricsSizeControl from "@/features/lyrics/components/LyricsSizeControl";
import VolumeChannel from "./VolumeChannel";
import MoreOptionsSheet from "./MoreOptionsSheet";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";

const PerformanceControlsPanel: React.FC = () => {
  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();

  const { isPlaying, currentTime, duration, userPlay, userPause, seek } =
    useKaraokePlayerStore();

  const [timingSheetOpen, setTimingSheetOpen] = useState(false);
  const [moreOptionsSheetOpen, setMoreOptionsSheetOpen] = useState(false);

  return (
    <div className="h-full flex flex-col gap-3 overflow-hidden">
      {/* Main controls area */}
      <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
        {/* Left: Primary vocals */}
        <VolumeChannel
          label="Vocals"
          icon={<Mic />}
          volume={vocalVolume}
          onVolumeChange={setVocalVolume}
          onToggleMute={toggleVocalsVolume}
          className="border-r border-orange-peel/30 pr-4 min-h-0"
        />

        {/* Right: Secondary controls */}
        <div className="flex flex-col gap-3 pl-4 min-h-0 overflow-y-auto">
          <VolumeChannel
            label="Backing"
            icon={<Music />}
            volume={backingVocalVolume}
            onVolumeChange={setBackingVocalVolume}
            onToggleMute={toggleBackingVocalsVolume}
            className="flex-1"
          />

        </div>
      </div>

      <div className="border-t border-orange-peel/30" />

      <div className="flex flex-col gap-3">
        <LyricsSizeControl />

        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => setTimingSheetOpen(true)}
        >
          <Timer size={14} className="mr-2" />
          Fix Lyrics Timing
        </Button>
      </div>

      <div className="border-t border-orange-peel/30 pt-3 flex flex-col gap-2 shrink-0">
        <div className="flex items-center justify-between">
          <Button
            className="rounded-full h-14 w-14 bg-gradient-to-br from-orange-peel to-rust hover:from-orange-peel/90 hover:to-rust/90 shadow-lg transition-all hover:scale-105"
            onClick={isPlaying ? userPause : userPlay}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause size={28} /> : <Play size={28} />}
          </Button>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-12 w-12 text-lemon-chiffon/70 hover:text-lemon-chiffon"
              onClick={() => setMoreOptionsSheetOpen(true)}
              aria-label="More options"
            >
              <Settings size={26} />
            </Button>

            <Button
              className="rounded-full h-14 w-14 bg-lemon-chiffon text-rust hover:bg-lemon-chiffon/90 shadow-lg transition-all hover:scale-105"
              onClick={() => sessionWebSocketService.toggleFullscreen()}
              aria-label="Toggle fullscreen on stage"
            >
              <Maximize size={28} />
            </Button>
          </div>
        </div>

        <ProgressBar
          currentTime={currentTime}
          duration={duration}
          onSeek={seek}
          className="w-full"
        />
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

      <MoreOptionsSheet
        open={moreOptionsSheetOpen}
        onOpenChange={setMoreOptionsSheetOpen}
      />
    </div>
  );
};

export default PerformanceControlsPanel;
