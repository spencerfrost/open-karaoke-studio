/**
 * LyricsSizeRow - "Size  [S][M][L]" on one line.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import type { LyricsSize } from "@/utils/performanceControls";
import type { Density } from "./density";

const SIZES: Array<{ value: LyricsSize; label: string }> = [
  { value: "small", label: "S" },
  { value: "medium", label: "M" },
  { value: "large", label: "L" },
];

interface LyricsSizeRowProps {
  density: Density;
}

const LyricsSizeRow: React.FC<LyricsSizeRowProps> = ({ density }) => {
  const isTv = density === "tv";
  const lyricsSize = useKaraokePlayerStore((state) => state.lyricsSize);
  const setLyricsSize = useKaraokePlayerStore((state) => state.setLyricsSize);

  return (
    <div className="flex items-center gap-3">
      <span
        className={cn(
          "flex-1 uppercase tracking-[0.08em] text-foreground/55",
          isTv ? "text-[15px]" : "text-xs",
        )}
      >
        Size
      </span>
      <div className="flex gap-2">
        {SIZES.map(({ value, label }) => {
          const isSelected = lyricsSize === value;

          return (
            <Button
              key={value}
              variant="ghost"
              onClick={() => setLyricsSize(value)}
              aria-pressed={isSelected}
              className={cn(
                "rounded-md border font-semibold",
                isTv ? "size-12 text-base" : "size-11 text-sm",
                isSelected
                  ? "border-glass-border/40 bg-glass/20 text-foreground"
                  : "border-glass-border/20 text-foreground/70",
              )}
            >
              {label}
            </Button>
          );
        })}
      </div>
    </div>
  );
};

export default LyricsSizeRow;
