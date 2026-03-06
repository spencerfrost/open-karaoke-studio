import React from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface MoreOptionsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const MoreOptionsSheet: React.FC<MoreOptionsSheetProps> = ({
  open,
  onOpenChange,
}) => {
  const { instrumentalVolume, setInstrumentalVolume, playbackSpeed, setPlaybackSpeed } =
    useKaraokePlayerStore();
  const { sessionId, displayCode } = useSessionStore();

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
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
  );
};

export default MoreOptionsSheet;
