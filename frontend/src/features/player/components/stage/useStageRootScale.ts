/**
 * useStageRootScale - sizes the performance screen to the viewport.
 *
 * Everything on the stage is laid out in rem (Tailwind's spacing and type are
 * rem-based), so scaling the root font size scales the whole screen as one
 * piece, keeping its proportions on any display. The stage was designed at
 * 1920x1080, where this resolves to the usual 16px; a TV browser that loses
 * ~140px to its own chrome gets a proportionally smaller stage instead of
 * rails that overflow.
 *
 * min(vh, vw) because height is the binding constraint on a 16:9 screen, but a
 * narrow or square window must not blow the rails past the width either.
 *
 * Only while the performance screen is up: song select scales its own fixed
 * frame to fit, and would shrink twice. Dialogs opened from the rails portal
 * to <body>, so they scale with the stage — which is what we want on the TV.
 */

import { useEffect } from "react";

/**
 * The one knob for how big the stage is. 1 = 16px root at 1920x1080; 1.1 is
 * 10% larger everywhere (rails, type, transport, lyrics).
 */
const STAGE_SCALE = 1.1;

// 16px is 1.4815% of 1080 and 0.8333% of 1920.
const STAGE_ROOT_FONT_SIZE = `min(${1.4815 * STAGE_SCALE}vh, ${0.8333 * STAGE_SCALE}vw)`;

export const useStageRootScale = (active: boolean) => {
  useEffect(() => {
    if (!active) return;

    const root = document.documentElement;
    const previous = root.style.fontSize;
    root.style.fontSize = STAGE_ROOT_FONT_SIZE;

    return () => {
      root.style.fontSize = previous;
    };
  }, [active]);
};
