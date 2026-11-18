/**
 * Swatches are the colours a theme gives *things*: a singer, a song or artist
 * with no art, a letter group. Each theme sets --swatch-1..6 in index.css; a
 * thing keeps the same swatch for as long as its key stays the same.
 *
 * Use them for a small piece only (a dot, an initial circle, a placeholder
 * tile), never to tint a whole row or screen.
 */

export const SWATCH_COUNT = 6;

/**
 * The full class names are listed so Tailwind generates them; never build
 * `bg-swatch-${n}` at runtime.
 */
const TILE = [
  "bg-swatch-1/20 text-swatch-1",
  "bg-swatch-2/20 text-swatch-2",
  "bg-swatch-3/20 text-swatch-3",
  "bg-swatch-4/20 text-swatch-4",
  "bg-swatch-5/20 text-swatch-5",
  "bg-swatch-6/20 text-swatch-6",
] as const;

const DOT = [
  "bg-swatch-1",
  "bg-swatch-2",
  "bg-swatch-3",
  "bg-swatch-4",
  "bg-swatch-5",
  "bg-swatch-6",
] as const;

/** A stable 0-based swatch index for a key: a number is used as-is, a string is hashed. */
export function swatchIndex(key: string | number): number {
  if (typeof key === "number") {
    return ((Math.trunc(key) % SWATCH_COUNT) + SWATCH_COUNT) % SWATCH_COUNT;
  }
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % SWATCH_COUNT;
}

/** A tinted tile with its icon or initial in the swatch colour. */
export function swatchTile(key: string | number): string {
  return TILE[swatchIndex(key)];
}

/** A solid dot in the swatch colour. */
export function swatchDot(key: string | number): string {
  return DOT[swatchIndex(key)];
}
