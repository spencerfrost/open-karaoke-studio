/**
 * MoreControlsSheet - the long tail: instrumental, auto-scroll,
 * session. Absorbs the old MoreOptionsSheet; lyrics size moved up into the
 * strip itself, so it is deliberately not repeated here.
 */

import React from "react";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useShallow } from "zustand/react/shallow";
import { cn } from "@/lib/utils";
import type { Density } from "./density";

interface MoreControlsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  density: Density;
}

const MoreControlsSheet: React.FC<MoreControlsSheetProps> = ({
  open,
  onOpenChange,
  density,
}) => {
  const isTv = density === "tv";

  const {
    instrumentalVolume,
    setInstrumentalVolume,
    autoScrollEnabled,
    setAutoScrollEnabled,
  } = useKaraokePlayerStore(
    useShallow((s) => ({
      instrumentalVolume: s.instrumentalVolume,
      setInstrumentalVolume: s.setInstrumentalVolume,
      autoScrollEnabled: s.autoScrollEnabled,
      setAutoScrollEnabled: s.setAutoScrollEnabled,
    })),
  );

  const sectionClass =
    "rounded-md border border-glass-border/10 bg-glass/5 p-4 flex flex-col gap-3";
  const sectionLabelClass = cn(
    "uppercase tracking-wide text-foreground-dim",
    isTv ? "text-sm" : "text-xs",
  );

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[85dvh] border-glass-border/10 bg-overlay/95 text-foreground backdrop-blur-md">
        <div className="overflow-y-auto pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          <DrawerHeader className="pb-2 text-left">
            <DrawerTitle className={isTv ? "text-xl" : "text-base"}>
              More Options
            </DrawerTitle>
          </DrawerHeader>

          <div className="mx-auto w-full max-w-2xl space-y-4 px-4 pb-2">
            {/* Instrumental volume */}
            <div className={sectionClass}>
              <span className={sectionLabelClass}>
                Instrumental Volume {Math.round(instrumentalVolume * 100)}%
              </span>
              <Slider
                value={[instrumentalVolume]}
                min={0}
                max={1}
                step={0.05}
                orientation="horizontal"
                onValueChange={([v]) => setInstrumentalVolume(v)}
                aria-label="Instrumental volume"
              />
            </div>

            {/* Auto-scroll toggle */}
            <div className="rounded-md border border-glass-border/10 bg-glass/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <Label
                  htmlFor="lyrics-auto-scroll"
                  className="text-sm text-foreground"
                >
                  Auto-scroll Lyrics
                </Label>
                <Switch
                  id="lyrics-auto-scroll"
                  checked={autoScrollEnabled}
                  onCheckedChange={setAutoScrollEnabled}
                />
              </div>
            </div>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
};

export default MoreControlsSheet;
