/**
 * TourLayer - the tour's highlight rings and its card.
 *
 * A thin layer over the shadcn Popover rather than a tour library. The card is
 * anchored to a virtual element that reads the target's box on every call,
 * and the popover repositions every frame (`updatePositionStrategy="always"`),
 * so it follows a target that moves or resizes while the stage re-renders.
 * The rings are framer-motion boxes over each target, sliding to its new box.
 *
 * Nothing here blocks the page: no dimming backdrop, the rings ignore the
 * pointer, and the popover is non-modal and never takes focus, so the wheel's
 * keyboard and the stage's controls keep working with the tour up.
 *
 * Everything renders inside the stage shell (the popover portals into a node
 * this layer owns), because the stage runs full screen and anything portalled
 * to <body> would be invisible there.
 */

import React, { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { findTourTarget, type TargetBox } from "../useTourTargets";

const RING_PADDING = 6;
const EDGE_GAP = 24;
/** The tour's card, shared by the anchored and the centred placements. */
const PANEL_CLASS = "w-[22rem] max-w-[calc(100vw-2rem)] p-5 shadow-2xl";

interface TourLayerProps {
  /** Every target to ring. */
  rings: TargetBox[];
  /** The target the card sits beside; corner placement when it isn't on screen. */
  anchorId: string | null;
  side?: "top" | "right" | "bottom" | "left";
  align?: "start" | "center" | "end";
  /** A card in the middle of the screen with no anchor (sound prompt, end card). */
  centered?: boolean;
  /** Changes per step, so each step's card animates in. */
  cardKey: string;
  children: React.ReactNode;
}

const TourLayer: React.FC<TourLayerProps> = ({
  rings,
  anchorId,
  side = "right",
  align = "center",
  centered = false,
  cardKey,
  children,
}) => {
  const reducedMotion = useReducedMotion() ?? false;
  const [portal, setPortal] = useState<HTMLDivElement | null>(null);
  // The caller only names an anchor it found on screen; it needn't be ringed.
  const anchored = anchorId !== null;

  // Read by the popover on every frame: the live box of the target, or a
  // point in the bottom-right corner when there's nothing to sit beside.
  const anchorRef = useRef({
    getBoundingClientRect: (): DOMRect =>
      new DOMRect(window.innerWidth - EDGE_GAP, window.innerHeight - EDGE_GAP),
  });
  anchorRef.current.getBoundingClientRect = () => {
    const el = anchored && anchorId ? findTourTarget(anchorId) : null;
    if (el) return el.getBoundingClientRect();
    return new DOMRect(
      window.innerWidth - EDGE_GAP,
      window.innerHeight - EDGE_GAP,
    );
  };

  return (
    <>
      <div ref={setPortal} />

      <div className="pointer-events-none fixed inset-0 z-[49]" aria-hidden>
        <AnimatePresence>
          {rings.map((box) => (
            <motion.div
              key={box.id}
              className="absolute rounded-xl ring-4 ring-primary shadow-[0_0_24px_4px] shadow-primary/40"
              initial={{
                opacity: 0,
                top: box.top - RING_PADDING,
                left: box.left - RING_PADDING,
                width: box.width + RING_PADDING * 2,
                height: box.height + RING_PADDING * 2,
              }}
              animate={{
                opacity: 1,
                top: box.top - RING_PADDING,
                left: box.left - RING_PADDING,
                width: box.width + RING_PADDING * 2,
                height: box.height + RING_PADDING * 2,
              }}
              exit={{ opacity: 0 }}
              transition={
                reducedMotion
                  ? { duration: 0 }
                  : { type: "spring", stiffness: 500, damping: 40 }
              }
            />
          ))}
        </AnimatePresence>
      </div>

      {centered ? (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            key={cardKey}
            role="dialog"
            aria-label="Guided tour"
            className={cn(
              "pointer-events-auto rounded-md border bg-popover text-popover-foreground",
              PANEL_CLASS,
            )}
            initial={reducedMotion ? false : { opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.div>
        </div>
      ) : (
        <Popover open modal={false}>
          <PopoverAnchor virtualRef={anchorRef} />
          {portal && (
            <PopoverContent
              key={cardKey}
              container={portal}
              side={anchored ? side : "top"}
              align={anchored ? align : "end"}
              sideOffset={anchored ? 18 : 0}
              collisionPadding={16}
              updatePositionStrategy="always"
              onOpenAutoFocus={(e) => e.preventDefault()}
              onCloseAutoFocus={(e) => e.preventDefault()}
              onInteractOutside={(e) => e.preventDefault()}
              onEscapeKeyDown={(e) => e.preventDefault()}
              aria-label="Guided tour"
              className={PANEL_CLASS}
            >
              {children}
            </PopoverContent>
          )}
        </Popover>
      )}
    </>
  );
};

export default TourLayer;
