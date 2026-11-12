/**
 * Shared classes for the stage rail's controls cards (MIX, LYRICS). The rail
 * is read from across the room and driven by a mouse on the mic stand, so the
 * type is large and the targets are mouse-sized.
 */

import { cn } from "@/lib/utils";

/** Outer shell of a controls card. */
export const cardClass = (className?: string) =>
  cn(
    "flex flex-col gap-3 rounded-md border border-glass-border/10 bg-glass/5 p-3.5",
    className,
  );

/** The small uppercase card heading ("MIX", "LYRICS"). */
export const cardLabelClass =
  "text-[0.9375rem] font-semibold uppercase tracking-[0.08em] text-foreground-dim";

/**
 * Size classes for the lucide icon that sits beside a card heading. Classes
 * rather than a pixel prop so the icon scales with the stage's rem.
 */
export const cardIconClass = "size-5";
