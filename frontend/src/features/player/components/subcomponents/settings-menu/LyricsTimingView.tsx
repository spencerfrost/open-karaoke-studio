/**
 * LyricsTimingView - Detailed lyrics controls with timing offset drag
 * Includes auto-scroll toggle, text size, timing offset with drag, and lyrics search/paste
 */

import React, { useState, useRef, useCallback } from "react";
import {
  ChevronLeft,
  Minus,
  Plus,
  RotateCcw,
  Save,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";
import { applyOffsetToLrc } from "@/utils/lrcUtils";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface LyricsTimingViewProps {
  onBack: () => void;
}

const LyricsTimingView: React.FC<LyricsTimingViewProps> = ({ onBack }) => {
  const songId = useKaraokePlayerStore((state) => state.songId);
  const lyricsOffset = useKaraokePlayerStore((state) => state.lyricsOffset);
  const setLyricsOffset = useKaraokePlayerStore(
    (state) => state.setLyricsOffset,
  );

  // Fetch current song for synced lyrics
  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  const updateSongMutation = useUpdateSong();

  // Drag state for timing offset
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [dragStartValue, setDragStartValue] = useState(0);
  const offsetRef = useRef<HTMLDivElement>(null);

  // Check if we can save (has synced lyrics and non-zero offset)
  const canSave = song?.syncedLyrics && lyricsOffset !== 0;

  const handleSaveOffset = useCallback(() => {
    if (!songId || !song?.syncedLyrics || lyricsOffset === 0) return;

    const updatedLyrics = applyOffsetToLrc(song.syncedLyrics, lyricsOffset);

    updateSongMutation.mutate(
      {
        id: songId,
        syncedLyrics: updatedLyrics,
      },
      {
        onSuccess: () => {
          setLyricsOffset(0); // Reset offset after save
        },
        onError: (error) => {
          toast.error(`Failed to save: ${error.message}`);
        },
      },
    );
  }, [
    songId,
    song?.syncedLyrics,
    lyricsOffset,
    updateSongMutation,
    setLyricsOffset,
  ]);

  const handleOffsetMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      setDragStartY(e.clientY);
      setDragStartValue(lyricsOffset);
      document.body.style.cursor = "ns-resize";
    },
    [lyricsOffset],
  );

  const handleOffsetMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      e.preventDefault();
      const deltaY = dragStartY - e.clientY; // Drag up = positive
      const sensitivity = 1; // pixels per 100ms step
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = dragStartValue + deltaSteps * 100;
      if (newValue !== lyricsOffset) {
        setLyricsOffset(newValue);
      }
    },
    [isDragging, dragStartY, dragStartValue, lyricsOffset, setLyricsOffset],
  );

  const handleOffsetMouseUp = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = "auto";
  }, []);

  // Touch support
  const handleOffsetTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      setIsDragging(true);
      setDragStartY(touch.clientY);
      setDragStartValue(lyricsOffset);
    },
    [lyricsOffset],
  );

  const handleOffsetTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!isDragging) return;
      e.preventDefault();
      const touch = e.touches[0];
      const deltaY = dragStartY - touch.clientY;
      const sensitivity = 1; // pixels per 100ms step
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = dragStartValue + deltaSteps * 100;
      if (newValue !== lyricsOffset) {
        setLyricsOffset(newValue);
      }
    },
    [isDragging, dragStartY, dragStartValue, lyricsOffset, setLyricsOffset],
  );

  const handleOffsetTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global event listeners for drag - CRITICAL cleanup
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleOffsetMouseMove);
      document.addEventListener("mouseup", handleOffsetMouseUp);
      document.addEventListener("touchmove", handleOffsetTouchMove, {
        passive: false,
      });
      document.addEventListener("touchend", handleOffsetTouchEnd);
      return () => {
        document.removeEventListener("mousemove", handleOffsetMouseMove);
        document.removeEventListener("mouseup", handleOffsetMouseUp);
        document.removeEventListener("touchmove", handleOffsetTouchMove);
        document.removeEventListener("touchend", handleOffsetTouchEnd);
      };
    }
  }, [
    isDragging,
    handleOffsetMouseMove,
    handleOffsetMouseUp,
    handleOffsetTouchMove,
    handleOffsetTouchEnd,
  ]);

  return (
    <div className="py-2">
      {/* Header with back button */}
      <div className="px-4 py-3 border-b border-white/10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 hover:text-orange-peel transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Lyrics</h2>
        </button>
      </div>

      {/* Content */}
      <div className="px-4 py-4 space-y-4">
        {/* Lyrics Offset - Drag to adjust */}
        <div className="space-y-2">
          <Label className="text-background">Timing Offset</Label>
          <div className="flex items-center gap-2">
            {/* Decrease button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLyricsOffset(lyricsOffset - 100)}
              className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
            >
              <Minus className="w-4 h-4" />
            </Button>

            {/* Draggable value display */}
            <div
              ref={offsetRef}
              className={cn(
                "flex-1 py-2 px-3 rounded-md bg-white/5 border border-white/10",
                "cursor-ns-resize select-none text-center font-mono text-lg",
                "hover:bg-white/10 hover:border-white/20 transition-colors",
                isDragging &&
                  "bg-white/15 border-orange-peel ring-1 ring-orange-peel",
              )}
              onMouseDown={handleOffsetMouseDown}
              onTouchStart={handleOffsetTouchStart}
            >
              <span className="text-background">
                {lyricsOffset > 0 ? "+" : ""}
                {lyricsOffset}ms
              </span>
            </div>

            {/* Increase button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLyricsOffset(lyricsOffset + 100)}
              className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
            >
              <Plus className="w-4 h-4" />
            </Button>

            {/* Reset button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLyricsOffset(0)}
              className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
              title="Reset to 0"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
          <div className="text-xs text-background/40 text-center">
            Drag up/down to adjust
          </div>

          {/* Save button - only show when offset is non-zero and song has synced lyrics */}
          {canSave && (
            <Button
              variant="default"
              size="sm"
              onClick={handleSaveOffset}
              disabled={updateSongMutation.isPending}
              className="w-full bg-orange-peel hover:bg-orange-peel/80"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Timing Adjustment
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LyricsTimingView;
