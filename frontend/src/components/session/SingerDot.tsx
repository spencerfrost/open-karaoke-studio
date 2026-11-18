import { cn } from "@/lib/utils";
import { singerSwatchKey, swatchDot } from "@/lib/swatch";

interface SingerDotProps {
  /** Their roster id; null for a song from before the roster. */
  performerId: number | null | undefined;
  name: string;
  /** Size it to the name it sits beside, e.g. `size-2.5` or `size-6`. */
  className?: string;
}

/**
 * The singer's colour, as a dot beside their name. Wherever someone's name is
 * shown, the same dot tells the room it's them; it never tints the row or
 * the name itself.
 */
export function SingerDot({ performerId, name, className }: SingerDotProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block size-2.5 shrink-0 rounded-full",
        swatchDot(singerSwatchKey(performerId, name)),
        className,
      )}
    />
  );
}
