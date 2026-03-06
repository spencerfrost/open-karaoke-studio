import React from "react";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface MoreOptionsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SPEED_PRESETS = [0.75, 0.9, 1, 1.5, 2];
const LYRICS_SIZE_PRESETS = ["small", "medium", "large"] as const;

const MoreOptionsSheet: React.FC<MoreOptionsSheetProps> = ({
  open,
  onOpenChange,
}) => {
  const {
    instrumentalVolume,
    setInstrumentalVolume,
    lyricsSize,
    setLyricsSize,
    playbackSpeed,
    setPlaybackSpeed,
    showChords,
    setShowChords,
  } = useKaraokePlayerStore();
  const { sessionId, displayCode } = useSessionStore();

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[85dvh] border-white/10 bg-black/95 text-background backdrop-blur-md">
        <div className="overflow-y-auto pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          <DrawerHeader className="pb-2 text-left">
            <DrawerTitle className="text-base font-semibold">
              More Options
            </DrawerTitle>
          </DrawerHeader>

          <div className="px-4 pb-2 space-y-4">
            {/* Instrumental volume */}
            <div className="rounded-md border border-white/10 bg-white/5 p-4 flex flex-col gap-3">
              <span className="text-xs uppercase tracking-wide text-background/70">
                Instrumental Volume {Math.round(instrumentalVolume * 100)}%
              </span>
              <Slider
                value={[instrumentalVolume]}
                min={0}
                max={1}
                step={0.05}
                orientation="horizontal"
                onValueChange={([v]) => setInstrumentalVolume(v)}
              />
            </div>

            {/* Playback speed */}
            <div className="rounded-md border border-white/10 bg-white/5 p-4 flex flex-col gap-3">
              <span className="text-xs uppercase tracking-wide text-background/70">
                Playback Speed {playbackSpeed.toFixed(2)}x
              </span>
              <Slider
                value={[playbackSpeed]}
                min={0.5}
                max={2}
                step={0.05}
                orientation="horizontal"
                onValueChange={([v]) => setPlaybackSpeed(v)}
              />
              <div className="flex flex-wrap gap-2 pt-1">
                {SPEED_PRESETS.map((preset) => {
                  const isSelected = Math.abs(playbackSpeed - preset) < 0.025;

                  return (
                    <Button
                      key={preset}
                      type="button"
                      variant="outline"
                      className={
                        isSelected
                          ? "h-9 min-w-14 border-white/40 bg-white/20 px-3 text-xs text-background hover:bg-white/20"
                          : "h-9 min-w-14 border-white/20 bg-transparent px-3 text-xs text-background hover:bg-white/10"
                      }
                      onClick={() => setPlaybackSpeed(preset)}
                    >
                      {preset}x
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Lyrics size */}
            <div className="rounded-md border border-white/10 bg-white/5 p-4 flex flex-col gap-3">
              <span className="text-xs uppercase tracking-wide text-background/70">
                Lyrics Size
              </span>
              <div className="flex gap-2">
                {LYRICS_SIZE_PRESETS.map((size) => {
                  const isSelected = lyricsSize === size;

                  return (
                    <Button
                      key={size}
                      type="button"
                      variant="outline"
                      className={
                        isSelected
                          ? "h-9 flex-1 border-white/40 bg-white/20 px-3 text-xs font-semibold uppercase text-background hover:bg-white/20"
                          : "h-9 flex-1 border-white/20 bg-transparent px-3 text-xs font-semibold uppercase text-background hover:bg-white/10"
                      }
                      onClick={() => setLyricsSize(size)}
                    >
                      {size === "small" ? "S" : size === "medium" ? "M" : "L"}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Guitar chords toggle */}
            <div className="rounded-md border border-white/10 bg-white/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <Label
                  htmlFor="show-guitar-chords"
                  className="text-sm text-background"
                >
                  Show Guitar Chords
                </Label>
                <Switch
                  id="show-guitar-chords"
                  checked={showChords}
                  onCheckedChange={setShowChords}
                />
              </div>
            </div>

            {/* Session info */}
            {sessionId && displayCode && (
              <div className="rounded-md border border-white/10 bg-white/5 p-4">
                <span className="mb-2 block text-xs uppercase tracking-wide text-background/70">
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
        </div>
      </DrawerContent>
    </Drawer>
  );
};

export default MoreOptionsSheet;
