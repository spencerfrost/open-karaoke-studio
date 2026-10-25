/**
 * LyricsOffsetRow - [−] [draggable readout] [+] [reset], plus save-to-LRC.
 *
 * Dragging the readout is the primary gesture; the flanking buttons are for
 * fine-tuning. A positive offset shows the lyrics earlier (see
 * describeLyricsOffset). Saving is useLyricsFixes' job; this row only offers
 * it, for a synced-lyrics song with a non-zero offset.
 */

import React from "react";
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
import {
  formatLyricsOffset,
  LYRICS_OFFSET_STEP_MS,
} from "@/utils/performanceControls";
import { cn } from "@/lib/utils";
import { useLyricsOffsetDrag } from "./useLyricsOffsetDrag";

/** Pixels of drag per step: an ordinary flick moves a few tenths, not seconds. */
const DRAG_PX_PER_STEP = 10;

interface LyricsOffsetRowProps {
  canSave: boolean;
  onSave: () => void;
  isSaving: boolean;
}

const LyricsOffsetRow: React.FC<LyricsOffsetRowProps> = ({
  canSave,
  onSave,
  isSaving,
}) => {
  const lyricsOffset = useKaraokePlayerStore((state) => state.lyricsOffset);
  const setLyricsOffset = useKaraokePlayerStore(
    (state) => state.setLyricsOffset,
  );

  const { isDragging, dragHandleProps } = useLyricsOffsetDrag({
    value: lyricsOffset,
    onChange: setLyricsOffset,
    step: LYRICS_OFFSET_STEP_MS,
    sensitivity: DRAG_PX_PER_STEP,
  });

  const flankClass =
    "size-11 shrink-0 rounded-md border border-primary text-primary";

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          className={flankClass}
          onClick={() => setLyricsOffset(lyricsOffset - LYRICS_OFFSET_STEP_MS)}
          aria-label="Show lyrics later"
        >
          <Minus className="size-5" strokeWidth={2.5} />
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
              setLyricsOffset(lyricsOffset + LYRICS_OFFSET_STEP_MS);
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              setLyricsOffset(lyricsOffset - LYRICS_OFFSET_STEP_MS);
            }
          }}
          className={cn(
            "flex h-11 min-w-0 flex-1 cursor-ns-resize select-none items-center justify-center gap-1.5 rounded-md",
            "border border-glass-border/20 bg-glass/5 transition-colors",
            "hover:border-glass-border/40 hover:bg-glass/10",
            isDragging && "border-primary bg-glass/15 ring-1 ring-primary",
          )}
        >
          <span className="font-accent text-3xl leading-none text-foreground">
            {formatLyricsOffset(lyricsOffset)}
          </span>
          <span className="flex flex-col gap-px text-foreground-faint">
            <ChevronUp className="size-3" strokeWidth={3} />
            <ChevronDown className="size-3" strokeWidth={3} />
          </span>
        </div>

        <Button
          variant="ghost"
          className={flankClass}
          onClick={() => setLyricsOffset(lyricsOffset + LYRICS_OFFSET_STEP_MS)}
          aria-label="Show lyrics earlier"
        >
          <Plus className="size-5" strokeWidth={2.5} />
        </Button>

        {/* Always rendered so clearing the offset never reflows the row */}
        <Button
          variant="ghost"
          className={cn(
            flankClass,
            "border-glass-border/20 text-foreground-dim",
            lyricsOffset === 0 && "opacity-40",
          )}
          disabled={lyricsOffset === 0}
          onClick={() => setLyricsOffset(0)}
          aria-label="Reset lyrics offset"
        >
          <RotateCcw className="size-5" />
        </Button>
      </div>

      {canSave && (
        <Button
          variant="primary"
          onClick={onSave}
          disabled={isSaving}
          className="h-11 w-full text-base"
        >
          <Save className="mr-2 size-4" />
          Save timing to song
        </Button>
      )}
    </div>
  );
};

export default LyricsOffsetRow;
