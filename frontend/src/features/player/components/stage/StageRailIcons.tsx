/**
 * StageRailIcons - the icon strips the rails show while a song plays.
 *
 * These are indicators, not controls: the real strip stays mounted behind
 * them and comes straight back the moment the mouse moves.
 */

import React from "react";
import {
  Captions,
  Grid2x2,
  Mic,
  MoreHorizontal,
  Search,
  SlidersHorizontal,
  Type,
} from "lucide-react";
import { cn } from "@/lib/utils";

const tileClass =
  "flex size-18 shrink-0 flex-col items-center justify-center gap-0.5 rounded-md border border-glass-border/15 bg-glass/5";

interface StageRailIconsProps {
  side: "left" | "right";
  queueCount?: number;
}

const StageRailIcons: React.FC<StageRailIconsProps> = ({
  side,
  queueCount = 0,
}) => (
  <div className="flex flex-col items-center gap-5 pt-2" aria-hidden="true">
    {side === "left" ? (
      <>
        <div className={tileClass}>
          <SlidersHorizontal className="size-7.5 text-foreground" />
        </div>
        <div className={tileClass}>
          <Search className="size-7.5 text-foreground" />
        </div>
        <div className={tileClass}>
          <Captions className="size-7.5 text-foreground" />
        </div>
        <div className={tileClass}>
          <Type className="size-7.5 text-foreground" />
        </div>
        <div className={cn(tileClass, "border-transparent bg-transparent")}>
          <MoreHorizontal className="size-7.5 text-foreground" />
        </div>
      </>
    ) : (
      <>
        <div className={tileClass}>
          <span className="font-accent text-[32px] leading-none text-primary">
            {queueCount}
          </span>
          <span className="text-[10px] uppercase tracking-[0.08em] text-foreground/60">
            Queue
          </span>
        </div>
        <div className={tileClass}>
          <Mic className="size-7.5 text-foreground" />
        </div>
        <div className={tileClass}>
          <Grid2x2 className="size-7.5 text-foreground" />
        </div>
      </>
    )}
  </div>
);

export default StageRailIcons;
