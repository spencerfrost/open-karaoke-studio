/**
 * Density tokens for the shared controls strip.
 *
 * The same components render on the stage ("tv" — read at 8 feet, driven by a
 * mouse on the mic stand) and on the performer's phone ("touch" — thumb-sized
 * targets). Only the type scale and hit areas differ; order, structure and
 * colour are identical so the two surfaces cannot drift apart.
 */

import { cn } from "@/lib/utils";

export type Density = "tv" | "touch";

/** Outer shell of a controls card (MIX, LYRICS). */
export const cardClass = (density: Density, className?: string) =>
  cn(
    "flex flex-col rounded-md border border-glass-border/10 bg-glass/5",
    density === "tv" ? "gap-3 p-3.5" : "gap-2.5 p-4",
    className,
  );

/** The small uppercase card heading ("MIX", "LYRICS"). */
export const cardLabelClass = (density: Density) =>
  cn(
    "font-semibold uppercase tracking-[0.08em] text-foreground/70",
    density === "tv" ? "text-[0.9375rem]" : "text-xs",
  );

/**
 * Size classes for the lucide icon that sits beside a card heading. Classes
 * rather than a pixel prop so the TV icon scales with the stage's rem.
 */
export const cardIconClass = (density: Density) =>
  density === "tv" ? "size-5" : "size-4";
