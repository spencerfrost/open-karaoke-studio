/**
 * WheelArtwork - an image slot for the song wheel: the songs heading's artist
 * photo, the info card's still and cover, and the blurred backdrop.
 *
 * Three rules, all from browsing at 30 rows a second:
 *
 * - **Keep the old image until the new one has loaded,** then fade across. A
 *   slot never flashes to empty between artists. The new image is decoded off
 *   the main thread before it is shown, so the fade does not stutter.
 * - **A failed image falls back and is not asked for again.** Sources are
 *   tried best first; one that fails is remembered for the rest of the page's
 *   life and skipped from then on.
 * - **Nothing loads = a letter tile,** when the slot has a letter to show.
 *   The backdrop has none and shows nothing.
 *
 * It does not decide *when* to load: callers pass sources only once the
 * cursor has settled (see useSongWheel).
 */

import React, { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

/** URLs that failed to load, for the life of the page. */
const failedUrls = new Set<string>();

interface WheelArtworkProps {
  /** Candidate images, best first. Empty entries are skipped. */
  sources: readonly (string | null | undefined)[];
  /** The letter tile's letter, when no source loads. Omit for no tile. */
  fallback?: string;
  /** Round for artists, rounded-square for songs. */
  shape?: "round" | "square";
  /** Sizes and places the slot. */
  className?: string;
  /** Applied to each image layer; the backdrop's blur goes here. */
  layerClassName?: string;
  fadeMs?: number;
}

const WheelArtwork: React.FC<WheelArtworkProps> = ({
  sources,
  fallback,
  shape = "square",
  className,
  layerClassName,
  fadeMs = 200,
}) => {
  const reducedMotion = useReducedMotion() ?? false;
  // Bumped when a source fails, so the next one is picked.
  const [, setFailures] = useState(0);
  const target =
    sources.find((s): s is string => !!s && !failedUrls.has(s)) ?? null;

  // The last image that finished loading. Shown until `target` catches up.
  const [loaded, setLoaded] = useState<string | null>(null);
  useEffect(() => {
    if (target === null || target === loaded) return;
    let cancelled = false;
    const img = new Image();
    img.src = target;
    img.decode().then(
      () => {
        if (!cancelled) setLoaded(target);
      },
      () => {
        failedUrls.add(target);
        if (!cancelled) setFailures((n) => n + 1);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [target, loaded]);

  // No source left at all: straight to the tile, nothing to wait for.
  const shown = target === null ? null : loaded;
  const fade = reducedMotion ? 0 : fadeMs / 1000;
  // The new layer fades in on top; the old one stays opaque underneath until
  // it is covered, so the fade never dips through to the background.
  const layer = {
    initial: { opacity: 0, zIndex: 2 },
    animate: { opacity: 1, zIndex: 2, transition: { duration: fade } },
    exit: {
      opacity: 0,
      zIndex: 1,
      transition: {
        opacity: { delay: fade, duration: 0 },
        zIndex: { duration: 0 },
      },
    },
  };

  return (
    <div
      aria-hidden
      className={cn(
        "relative overflow-hidden [container-type:size]",
        shape === "round" ? "rounded-full" : "rounded-xl",
        className,
      )}
    >
      <AnimatePresence initial={false}>
        {shown !== null ? (
          <motion.img
            key={shown}
            src={shown}
            alt=""
            draggable={false}
            className={cn(
              "absolute inset-0 size-full object-cover",
              layerClassName,
            )}
            {...layer}
          />
        ) : fallback !== undefined ? (
          <motion.div
            key={`tile:${fallback}`}
            className="absolute inset-0 grid place-items-center bg-surface font-display text-[52cqmin] font-extrabold leading-none text-foreground/55 ring-1 ring-inset ring-border/30"
            {...layer}
          >
            {fallback}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
};

export default WheelArtwork;
