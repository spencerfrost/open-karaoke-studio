/**
 * LyricsOffsetRow - [−] [draggable readout] [+] [reset], plus save-to-LRC.
 *
 * Dragging the readout is the primary gesture; the flanking buttons are for
 * fine-tuning. Saving bakes the offset into the song's LRC and resets it, and
 * is only possible for a synced-lyrics song with a non-zero offset.
 */

import React, { useCallback } from "react";
import {
  Minus,
  Plus,
  RotateCcw,
  Save,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";
import { applyOffsetToLrc } from "@/utils/lrcUtils";
import { formatLyricsOffset } from "@/utils/performanceControls";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useLyricsOffsetDrag } from "./useLyricsOffsetDrag";
import type { Density } from "./density";

const OFFSET_STEP_MS = 100;

interface LyricsOffsetRowProps {
  density: Density;
}

const LyricsOffsetRow: React.FC<LyricsOffsetRowProps> = ({ density }) => {
  const isTv = density === "tv";

  const songId = useKaraokePlayerStore((state) => state.songId);
  const lyricsOffset = useKaraokePlayerStore((state) => state.lyricsOffset);
  const setLyricsOffset = useKaraokePlayerStore(
    (state) => state.setLyricsOffset,
  );

  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  const updateSongMutation = useUpdateSong();

  const { isDragging, dragHandleProps } = useLyricsOffsetDrag({
    value: lyricsOffset,
    onChange: setLyricsOffset,
    step: OFFSET_STEP_MS,
  });

  const canSave = !!song?.syncedLyrics && lyricsOffset !== 0;

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

  const flankClass = cn(
    "shrink-0 border border-primary text-primary rounded-md",
    isTv ? "size-16" : "h-13 w-12",
  );

  return (
    <div className="flex flex-col gap-2.5">
      <div className={cn("flex items-center", isTv ? "gap-2.5" : "gap-2")}>
        <Button
          variant="ghost"
          className={flankClass}
          onClick={() => setLyricsOffset(lyricsOffset - OFFSET_STEP_MS)}
          aria-label="Nudge lyrics earlier"
        >
          <Minus className={isTv ? "size-6.5" : "size-5.5"} strokeWidth={2.5} />
        </Button>

        <div
          {...dragHandleProps}
          role="slider"
          tabIndex={0}
          aria-label="Lyrics timing offset"
          aria-valuenow={lyricsOffset}
          aria-valuetext={formatLyricsOffset(lyricsOffset)}
          onKeyDown={(e) => {
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setLyricsOffset(lyricsOffset + OFFSET_STEP_MS);
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              setLyricsOffset(lyricsOffset - OFFSET_STEP_MS);
            }
          }}
          className={cn(
            "flex flex-1 cursor-ns-resize select-none items-center justify-center gap-2 rounded-md",
            "border border-glass-border/20 bg-glass/5 transition-colors",
            "hover:border-glass-border/40 hover:bg-glass/10",
            isTv ? "h-16" : "h-13",
            isDragging && "border-primary bg-glass/15 ring-1 ring-primary",
          )}
        >
          <span
            className={cn(
              "font-accent leading-none text-foreground",
              isTv ? "text-[40px]" : "text-[34px]",
            )}
          >
            {formatLyricsOffset(lyricsOffset)}
          </span>
          <span className="flex flex-col gap-px text-foreground/40">
            <ChevronUp
              className={isTv ? "size-3.5" : "size-3"}
              strokeWidth={3}
            />
            <ChevronDown
              className={isTv ? "size-3.5" : "size-3"}
              strokeWidth={3}
            />
          </span>
        </div>

        <Button
          variant="ghost"
          className={flankClass}
          onClick={() => setLyricsOffset(lyricsOffset + OFFSET_STEP_MS)}
          aria-label="Nudge lyrics later"
        >
          <Plus className={isTv ? "size-6.5" : "size-5.5"} strokeWidth={2.5} />
        </Button>

        {/* Always rendered so clearing the offset never reflows the row */}
        <Button
          variant="ghost"
          className={cn(
            flankClass,
            "border-glass-border/20 text-foreground/70",
            lyricsOffset === 0 && "opacity-40",
          )}
          disabled={lyricsOffset === 0}
          onClick={() => setLyricsOffset(0)}
          aria-label="Reset lyrics offset"
        >
          <RotateCcw className={isTv ? "size-6" : "size-5"} />
        </Button>
      </div>

      {canSave && (
        <Button
          variant="primary"
          onClick={handleSaveOffset}
          disabled={updateSongMutation.isPending}
          className={cn("w-full", isTv ? "h-14 text-lg" : "h-11")}
        >
          <Save className="mr-2 size-4" />
          Save timing to song
        </Button>
      )}
    </div>
  );
};

export default LyricsOffsetRow;
