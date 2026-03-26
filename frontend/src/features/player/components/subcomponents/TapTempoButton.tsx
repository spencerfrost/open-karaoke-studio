import React, { useEffect, useRef, useState } from "react";
import { Activity, Save, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface TapTempoButtonProps {
  bpm: number | null; // Current BPM from song or tap tempo
  songBpm: number | null; // Original song BPM from database
  isPlaying: boolean; // Whether the song is currently playing
  isActive: boolean; // Whether tap tempo is actively being used
  tapCount: number; // Number of taps registered
  minTaps: number; // Minimum taps required before BPM is set
  hasUnsavedChanges: boolean; // Whether there are unsaved BPM changes
  onTap: () => void;
  onSave: () => void;
  onReset: () => void;
  isSaving?: boolean;
  className?: string;
}

/**
 * TapTempoButton - A button that pulses with the beat and allows tap tempo input
 * Shows in the bottom left corner of the player, pulses with current BPM
 * Includes save and reset buttons when BPM is adjusted
 */
export const TapTempoButton: React.FC<TapTempoButtonProps> = ({
  bpm,
  songBpm,
  isPlaying,
  isActive,
  tapCount,
  minTaps,
  hasUnsavedChanges,
  onTap,
  onSave,
  onReset,
  isSaving = false,
  className,
}) => {
  const [isPulsing, setIsPulsing] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const pulseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pulseIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Pulse animation based on BPM - only when playing
  useEffect(() => {
    // Clear any existing timers
    if (pulseTimerRef.current) {
      clearTimeout(pulseTimerRef.current);
    }
    if (pulseIntervalRef.current) {
      clearInterval(pulseIntervalRef.current);
    }

    // Only pulse when song is playing and we have a BPM
    if (bpm && bpm > 0 && isPlaying) {
      // Calculate interval in milliseconds
      const intervalMs = 60000 / bpm;

      // Start pulsing immediately
      setIsPulsing(true);
      pulseTimerRef.current = setTimeout(() => {
        setIsPulsing(false);
      }, 150); // Pulse duration

      // Set up interval for continuous pulsing
      pulseIntervalRef.current = setInterval(() => {
        setIsPulsing(true);
        setTimeout(() => {
          setIsPulsing(false);
        }, 150);
      }, intervalMs);
    } else {
      setIsPulsing(false);
    }

    return () => {
      if (pulseTimerRef.current) {
        clearTimeout(pulseTimerRef.current);
      }
      if (pulseIntervalRef.current) {
        clearInterval(pulseIntervalRef.current);
      }
    };
  }, [bpm, isPlaying]);

  // Determine button state
  const showTapCount = isActive && tapCount < minTaps;
  const showBpm = bpm !== null;
  const bpmChanged = bpm !== null && bpm !== songBpm;

  // Determine pulse intensity based on hover state
  const pulseScale = isHovering ? "scale-110" : "scale-105";
  const pulseBg = isHovering ? "bg-orange-peel/20" : "bg-orange-peel/10";
  const pulseIconScale = isHovering ? "scale-125" : "scale-110";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Save button - show when BPM has changed */}
      {bpmChanged && (
        <>
          <Button
            size="sm"
            onClick={onSave}
            disabled={isSaving}
            className={cn(
              "h-9 px-3 bg-orange-peel hover:bg-orange-peel/90",
              "border border-orange-peel/50",
              hasUnsavedChanges && "animate-pulse",
            )}
            title="Save BPM to song"
          >
            <Save className="w-4 h-4" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={onReset}
            className="h-9 px-3 bg-black/40 hover:bg-black/60 border border-orange-peel/30 hover:border-orange-peel/60"
            title={
              songBpm ? `Reset to ${songBpm.toFixed(1)} BPM` : "Clear tempo"
            }
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
        </>
      )}
      <button
        onClick={onTap}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className={cn(
          "flex items-center gap-2 rounded-lg transition-all duration-200",
          "text-foreground/80 hover:text-foreground",
          isHovering
            ? "px-3 py-2 bg-black/60 border border-orange-peel/60"
            : "px-1 py-1 border border-transparent",
          isPulsing && !isHovering && "scale-105",
          isPulsing && isHovering && "scale-110 bg-orange-peel/20 border-orange-peel",
          isActive && isHovering && "bg-orange-peel/10 border-orange-peel/50",
        )}
        title={
          showTapCount
            ? `Tap ${minTaps - tapCount} more time${minTaps - tapCount === 1 ? "" : "s"}`
            : showBpm
              ? `${bpm!.toFixed(1)} BPM - Click or press T to adjust`
              : "Tap to set tempo"
        }
        aria-label="Tap tempo"
      >
        <Activity
          className={cn(
            "w-5 h-5 transition-all duration-150",
            isPulsing && `text-orange-peel ${pulseIconScale}`,
            isActive && "text-orange-peel",
          )}
        />
        <div
          className={cn(
            "flex flex-col items-start text-xs leading-tight overflow-hidden transition-all duration-200",
            isHovering ? "max-w-[4rem] opacity-100" : "max-w-0 opacity-0",
          )}
        >
          {showTapCount ? (
            <>
              <span className="font-semibold text-orange-peel whitespace-nowrap">
                {tapCount}/{minTaps}
              </span>
              <span className="text-[10px] text-foreground/60 whitespace-nowrap">taps</span>
            </>
          ) : showBpm ? (
            <>
              <span className="font-semibold whitespace-nowrap">{bpm!.toFixed(1)}</span>
              <span className="text-[10px] text-foreground/60 whitespace-nowrap">BPM</span>
            </>
          ) : (
            <>
              <span className="font-semibold whitespace-nowrap">Tap</span>
              <span className="text-[10px] text-foreground/60 whitespace-nowrap">tempo</span>
            </>
          )}
        </div>
      </button>
    </div>
  );
};
