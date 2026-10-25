/**
 * PhoneFader - one tall vocal fader for a thumb: name, percentage with the
 * mute beside it, and a fader that takes all the height its column has.
 *
 * A channel the song can't provide (a two-track song has no backup singers)
 * shows why in its place at the same size, so the layout never shifts.
 */

import React from "react";
import { Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import { phonePanelClass } from "./phoneStyles";

interface PhoneFaderProps {
  label: string;
  volume: number;
  onVolumeChange: (volume: number) => void;
  onToggleMute: () => void;
  /** Set when the song has no such track; shown in place of the fader. */
  unavailableReason?: string;
  /** `data-tour` target for the guided demo's tour. */
  tourId?: string;
}

const PhoneFader: React.FC<PhoneFaderProps> = ({
  label,
  volume,
  onVolumeChange,
  onToggleMute,
  unavailableReason,
  tourId,
}) => {
  if (unavailableReason) {
    return (
      <div
        data-tour={tourId}
        className="flex min-h-0 flex-col items-center justify-center gap-2 rounded-md border border-dashed border-glass-border/20 p-4 text-center"
      >
        <span className="text-lg font-semibold text-foreground">{label}</span>
        <span className="text-base leading-snug text-foreground-dim">
          {unavailableReason}
        </span>
      </div>
    );
  }

  const isMuted = volume === 0;

  return (
    <div
      data-tour={tourId}
      className={cn(
        phonePanelClass,
        "flex min-h-0 flex-col items-center gap-1.5 p-2.5",
      )}
    >
      <span className="text-base font-semibold leading-tight text-foreground">
        {label}
      </span>

      {/* The mute sits beside the level it zeroes, so it costs no row of its
          own; still a full 44 px target. */}
      <div className="flex w-full items-center justify-center gap-2">
        <span className="font-accent text-3xl leading-none text-primary">
          {Math.round(volume * 100)}%
        </span>
        <Button
          variant="ghost"
          onClick={onToggleMute}
          aria-pressed={isMuted}
          aria-label={`${isMuted ? "Unmute" : "Mute"} ${label}`}
          className={cn(
            "size-11 shrink-0 rounded-md border",
            isMuted
              ? "border-primary bg-primary/15 text-foreground"
              : "border-glass-border/20 text-foreground-dim",
          )}
        >
          {isMuted ? (
            <VolumeX className="size-5" />
          ) : (
            <Volume2 className="size-5" />
          )}
        </Button>
      </div>

      <div className="flex min-h-0 w-full flex-1 justify-center">
        {/* The slider sets touch-action: none on itself, so dragging it never
            scrolls the page, and nothing else on the page needs to. */}
        <Slider
          value={[volume]}
          min={0}
          max={1}
          step={0.05}
          variant="performance"
          orientation="vertical"
          onValueChange={([v]) => onVolumeChange(v)}
          // A thumb-height handle (44 px) rather than the stage's 56 px, so
          // more of a short track is travel.
          className="h-full data-[orientation=vertical]:min-h-24"
          thumbClassName="h-11 w-20"
          aria-label={`${label} volume`}
        />
      </div>
    </div>
  );
};

export default PhoneFader;
