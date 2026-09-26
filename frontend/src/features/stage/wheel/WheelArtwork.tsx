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
 * Dimming lives here too, on the image itself, not on a wrapper: an image that
 * no longer matches the cursor (`pending`, or the next one still loading)
 * sits at `staleOpacity`, and only the next image arriving brightens the slot.
 * A wrapper that dimmed on its own clock brightened the *old* image back up
 * the moment the cursor settled, and then swapped it - a flash on every move.
 *
 * It does not decide *when* to load: callers pass sources only once the
 * cursor has settled (see useSongWheel).
 */

import React, { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

/** URLs that failed to load, for the life of the page. */
const failedUrls = new Set<string>();

/**
 * One thing the slot has shown: an image, or the letter tile. Each change of
 * what is shown is a new layer, even back to an image still fading out, so a
 * leaving layer is never revived mid-exit.
 */
interface Layer {
  key: number;
  /** The image, or null for the letter tile. */
  src: string | null;
  letter?: string;
  /** Replaced: sits under the new layer, then fades out and is dropped. */
  leaving: boolean;
  /** There when the slot mounted: appears without fading in. */
  mounted: boolean;
}

const sameContent = (
  layer: Layer | undefined,
  src: string | null,
  letter?: string,
) =>
  layer !== undefined &&
  layer.src === src &&
  (src !== null || layer.letter === letter);

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
  /** The cursor has moved off what `sources` are for and not settled yet. */
  pending?: boolean;
  /**
   * Opacity of an image that is out of date: while `pending`, and while the
   * next image loads. 1 = never dimmed (the backdrop).
   */
  staleOpacity?: number;
  fadeMs?: number;
}

const WheelArtwork: React.FC<WheelArtworkProps> = ({
  sources,
  fallback,
  shape = "square",
  className,
  layerClassName,
  pending = false,
  staleOpacity = 1,
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
  const hasContent = shown !== null || fallback !== undefined;

  const [layers, setLayers] = useState<Layer[]>(() =>
    hasContent
      ? [
          {
            key: 0,
            src: shown,
            letter: fallback,
            leaving: false,
            mounted: true,
          },
        ]
      : [],
  );
  // Only the newest layer can be current; everything under it is leaving.
  const newest = layers[layers.length - 1] as Layer | undefined;
  const current = newest?.leaving ? undefined : newest;
  const upToDate = hasContent
    ? sameContent(current, shown, fallback)
    : current === undefined;
  if (!upToDate) {
    // Adjusting state during render: the new layer is in the very next paint.
    const key = (newest?.key ?? -1) + 1;
    setLayers([
      // With no fade there is nothing to wait for: the old ones just go.
      ...(fadeMs > 0 && !reducedMotion
        ? layers.map((l) => (l.leaving ? l : { ...l, leaving: true }))
        : []),
      ...(hasContent
        ? [
            {
              key,
              src: shown,
              letter: fallback,
              leaving: false,
              mounted: false,
            },
          ]
        : []),
    ]);
  }
  const drop = (key: number) =>
    setLayers((ls) => ls.filter((l) => l.key !== key));

  const ms = reducedMotion ? 0 : fadeMs;
  // Three properties, three elements, so none fights another for `opacity`:
  // the outer one leaves, the middle one dims, the inner one arrives. The new
  // layer fades in on top; the old one stays underneath until it is covered,
  // then fades out - usually unseen, but a new layer that arrives dimmed does
  // not fully cover it, and a snap would show.
  return (
    <div
      aria-hidden
      className={cn(
        "relative overflow-hidden [container-type:size]",
        shape === "round" ? "rounded-full" : "rounded-xl",
        className,
      )}
    >
      {layers.map((l) => {
        const stale =
          l.leaving || pending || (l.src !== null && l.src !== target);
        return (
          <div
            key={l.key}
            className={cn("absolute inset-0", l.leaving ? "z-[1]" : "z-[2]")}
            style={
              l.leaving
                ? { animation: `wheel-art-out ${ms}ms linear ${ms}ms both` }
                : undefined
            }
            onAnimationEnd={(e) => {
              if (e.target === e.currentTarget && l.leaving) drop(l.key);
            }}
          >
            <div
              className="absolute inset-0"
              style={{
                opacity: stale ? staleOpacity : 1,
                transition: `opacity ${ms}ms`,
              }}
            >
              {l.src !== null ? (
                <img
                  src={l.src}
                  alt=""
                  draggable={false}
                  className={cn(
                    "absolute inset-0 size-full object-cover",
                    layerClassName,
                  )}
                  style={
                    l.mounted
                      ? undefined
                      : { animation: `wheel-art-in ${ms}ms both` }
                  }
                />
              ) : (
                <div
                  className="absolute inset-0 grid place-items-center bg-surface font-display text-[52cqmin] font-extrabold leading-none text-foreground/55 ring-1 ring-inset ring-border/30"
                  style={
                    l.mounted
                      ? undefined
                      : { animation: `wheel-art-in ${ms}ms both` }
                  }
                >
                  {l.letter}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default WheelArtwork;
