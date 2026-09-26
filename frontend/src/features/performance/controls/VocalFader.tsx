/**
 * VocalFader - one channel strip: name row with mute, VT323 readout, fader.
 *
 * The fader is always visible and never hidden behind a button. A channel the
 * current song cannot provide (a two-track song has no backing vocal) renders
 * disabled at 0 with a hint laid over the track, so the layout never reflows.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Density } from "./density";

interface VocalFaderProps {
  label: string;
  icon: React.ReactNode;
  volume: number;
  onVolumeChange: (volume: number) => void;
  onToggleMute: () => void;
  density: Density;
  disabled?: boolean;
  /** Shown over the track when disabled — explains why the channel is dead. */
  disabledHint?: string;
}

const VocalFader: React.FC<VocalFaderProps> = ({
  label,
  icon,
  volume,
  onVolumeChange,
  onToggleMute,
  density,
  disabled = false,
  disabledHint,
}) => {
  const isTv = density === "tv";
  const isMuted = volume === 0;

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col items-center gap-2.5",
        disabled && "opacity-50",
      )}
    >
      {/* Name row — the mute lives here, not as a separate button */}
      <div
        className={cn("flex w-full items-center", isTv ? "gap-1" : "gap-1.5")}
      >
        <span className="shrink-0 text-primary">
          {React.cloneElement(
            icon as React.ReactElement<{ className?: string }>,
            { className: isTv ? "size-4.5" : "size-4" },
          )}
        </span>
        <span
          className={cn(
            "min-w-0 flex-1 truncate font-semibold",
            isTv ? "text-[0.9375rem]" : "text-sm",
          )}
        >
          {label}
        </span>
        <Button
          variant="ghost"
          size="icon"
          disabled={disabled}
          onClick={onToggleMute}
          aria-label={isMuted ? `Unmute ${label}` : `Mute ${label}`}
          className={cn(
            "shrink-0 text-foreground/55 hover:text-foreground",
            "size-8",
          )}
        >
          {isMuted ? (
            <VolumeX className={isTv ? "size-5" : "size-4.5"} />
          ) : (
            <Volume2 className={isTv ? "size-5" : "size-4.5"} />
          )}
        </Button>
      </div>

      <div
        className={cn(
          "font-accent leading-none text-primary",
          isTv ? "text-[2rem]" : "text-[30px]",
        )}
      >
        {Math.round(volume * 100)}%
      </div>

      <div className="relative flex min-h-0 w-full flex-1 justify-center">
        <Slider
          value={[volume]}
          min={0}
          max={1}
          step={0.05}
          variant="performance"
          orientation="vertical"
          disabled={disabled}
          onValueChange={([v]) => onVolumeChange(v)}
          // On the TV the thumb is a mouse target, not a thumb target, and the
          // fader may shrink well below the phone's floor on a short screen.
          className={cn(
            "h-full",
            isTv && "data-[orientation=vertical]:min-h-20",
          )}
          thumbClassName={isTv ? "h-10 w-16" : undefined}
          aria-label={`${label} volume`}
        />
        {disabled && disabledHint && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <span
              className={cn(
                "max-w-full rounded-sm bg-overlay/70 px-2 py-1 text-center leading-tight text-foreground/70",
                isTv ? "text-sm" : "text-[11px]",
              )}
            >
              {disabledHint}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default VocalFader;
