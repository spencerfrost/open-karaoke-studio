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

interface VocalFaderProps {
  label: string;
  icon: React.ReactNode;
  volume: number;
  onVolumeChange: (volume: number) => void;
  onToggleMute: () => void;
  disabled?: boolean;
  /** Shown over the track when disabled — explains why the channel is dead. */
  disabledHint?: string;
  /** `data-tour` target for the guided demo's tour. */
  tourId?: string;
}

const VocalFader: React.FC<VocalFaderProps> = ({
  label,
  icon,
  volume,
  onVolumeChange,
  onToggleMute,
  disabled = false,
  disabledHint,
  tourId,
}) => {
  const isMuted = volume === 0;

  return (
    <div
      data-tour={tourId}
      className={cn(
        "flex min-h-0 flex-col items-center gap-2.5",
        disabled && "opacity-50",
      )}
    >
      {/* Name row — the mute lives here, not as a separate button */}
      <div className="flex w-full items-center gap-1">
        <span className="shrink-0 text-primary">
          {React.cloneElement(
            icon as React.ReactElement<{ className?: string }>,
            { className: "size-4.5" },
          )}
        </span>
        <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-semibold">
          {label}
        </span>
        <Button
          variant="ghost"
          size="icon"
          disabled={disabled}
          onClick={onToggleMute}
          aria-label={isMuted ? `Unmute ${label}` : `Mute ${label}`}
          className="size-8 shrink-0 text-foreground-dim hover:text-foreground"
        >
          {isMuted ? (
            <VolumeX className="size-5" />
          ) : (
            <Volume2 className="size-5" />
          )}
        </Button>
      </div>

      <div className="font-accent text-[2rem] leading-none text-primary">
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
          // The thumb is a mouse target, not a finger target, and the fader
          // may shrink well below the slider's default floor on a short TV.
          className="h-full data-[orientation=vertical]:min-h-20"
          thumbClassName="h-10 w-16"
          aria-label={`${label} volume`}
        />
        {disabled && disabledHint && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <span className="max-w-full rounded-sm bg-overlay/70 px-2 py-1 text-center text-sm leading-tight text-foreground-dim">
              {disabledHint}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default VocalFader;
