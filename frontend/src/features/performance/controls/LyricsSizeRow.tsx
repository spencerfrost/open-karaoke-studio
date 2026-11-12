/**
 * LyricsSizeRow - "Size  [S][M][L]" on one line.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { cn } from "@/lib/utils";
import type { LyricsSize } from "@/utils/performanceControls";

const SIZES: Array<{ value: LyricsSize; label: string }> = [
  { value: "small", label: "S" },
  { value: "medium", label: "M" },
  { value: "large", label: "L" },
];

const LyricsSizeRow: React.FC = () => {
  const lyricsSize = useKaraokePlayerStore((state) => state.lyricsSize);
  const setLyricsSize = useKaraokePlayerStore((state) => state.setLyricsSize);

  return (
    <div className="flex items-center gap-3">
      <span className="flex-1 text-sm uppercase tracking-[0.08em] text-foreground-dim">
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
                "size-10 rounded-md border text-base font-semibold",
                isSelected
                  ? "border-glass-border/40 bg-glass/20 text-foreground"
                  : "border-glass-border/20 text-foreground-dim",
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
