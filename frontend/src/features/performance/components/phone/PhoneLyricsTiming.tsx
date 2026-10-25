/**
 * PhoneLyricsTiming - Earlier / Later buttons either side of the offset,
 * under a line saying what it means. That line doubles as the heading, so
 * the row costs one line less of the faders' height.
 *
 * Press and drag the number for big moves (up is earlier); tap Earlier or
 * Later for a single step, the same step as the stage rail and keyboard.
 * A positive offset shows each line sooner (see describeLyricsOffset).
 */

import React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import {
  describeLyricsOffset,
  formatLyricsOffset,
  LYRICS_OFFSET_STEP_MS,
} from "@/utils/performanceControls";
import { useLyricsOffsetDrag } from "../../controls/useLyricsOffsetDrag";
import { phonePanelClass } from "./phoneStyles";

/** Pixels of drag per step: a 50 px drag moves the lyrics a second. */
const DRAG_PX_PER_STEP = 5;

const nudgeClass =
  "h-12 flex-1 rounded-md border border-primary text-lg font-semibold text-primary";

const PhoneLyricsTiming: React.FC = () => {
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

  return (
    <div
      role="group"
      aria-label="Lyrics timing"
      className={cn(
        phonePanelClass,
        "flex shrink-0 flex-col gap-1.5 p-2.5 pt-1",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <p
          className="min-w-0 truncate pl-0.5 text-base text-foreground-dim"
          aria-live="polite"
        >
          {describeLyricsOffset(lyricsOffset)}
        </p>
        {/* Always rendered, so clearing the offset never shifts the row */}
        <Button
          variant="ghost"
          disabled={lyricsOffset === 0}
          onClick={() => setLyricsOffset(0)}
          className="-mr-1 h-10 shrink-0 px-3 text-base font-semibold"
        >
          Reset
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          className={nudgeClass}
          onClick={() => setLyricsOffset(lyricsOffset + LYRICS_OFFSET_STEP_MS)}
        >
          Earlier
        </Button>

        {/* touch-none: the drag must not scroll the page under it */}
        <div
          {...dragHandleProps}
          role="slider"
          tabIndex={0}
          aria-label="Lyrics timing offset"
          aria-valuenow={lyricsOffset}
          aria-valuetext={describeLyricsOffset(lyricsOffset)}
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
            "flex h-12 min-w-0 flex-1 cursor-ns-resize touch-none select-none items-center justify-center gap-1 rounded-md",
            "border border-glass-border/20 bg-glass/5 transition-colors",
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
          className={nudgeClass}
          onClick={() => setLyricsOffset(lyricsOffset - LYRICS_OFFSET_STEP_MS)}
        >
          Later
        </Button>
      </div>
    </div>
  );
};

export default PhoneLyricsTiming;
