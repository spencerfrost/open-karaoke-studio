import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Timer, Settings, Mic, Music } from "lucide-react";
import { usePerformanceControlsLogic } from "../hooks/usePerformanceControlsLogic";
import LyricsTimingControls from "@/features/lyrics/components/LyricsTimingControls";
import LyricsSizeControl from "@/features/lyrics/components/LyricsSizeControl";
import VolumeChannel from "./VolumeChannel";
import MoreOptionsSheet from "./MoreOptionsSheet";
import PerformanceTransportBar from "./PerformanceTransportBar";

const PerformanceControlsPanel: React.FC = () => {
  const {
    vocalVolume,
    backingVocalVolume,
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    setVocalVolume,
    setBackingVocalVolume,
  } = usePerformanceControlsLogic();

  const [timingSheetOpen, setTimingSheetOpen] = useState(false);
  const [moreOptionsSheetOpen, setMoreOptionsSheetOpen] = useState(false);

  return (
    <div className="h-full flex flex-col gap-3 overflow-hidden">
      {/* Main controls area */}
      <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
        {/* Left: Primary vocals (hero) */}
        <VolumeChannel
          label="Vocals"
          icon={<Mic />}
          volume={vocalVolume}
          onVolumeChange={setVocalVolume}
          onToggleMute={toggleVocalsVolume}
          variant="hero"
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
            variant="secondary"
            className="flex-1"
          />

          <div className="border-t border-orange-peel/20" />

          <LyricsSizeControl />

          <div className="border-t border-orange-peel/20" />

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => setTimingSheetOpen(true)}
          >
            <Timer size={14} className="mr-2" />
            Fix Lyrics Timing
          </Button>

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

      <PerformanceTransportBar />

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
