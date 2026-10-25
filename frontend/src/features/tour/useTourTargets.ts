/**
 * useTourTargets - where the tour's `data-tour` targets are on screen, live.
 *
 * Looked up by attribute every frame while a step is showing, not once: the
 * stage re-renders and moves things all the time (screens swap, the rails
 * collapse while a song plays, the processing list grows a row, the song
 * select screen is hidden rather than unmounted). A target inside a hidden
 * screen has no box, so it counts as not on screen.
 *
 * Only sets state when a box actually moves, so a still page costs one
 * querySelectorAll and a few getBoundingClientRect calls per frame.
 */

import { useEffect, useState } from "react";

export interface TargetBox {
  id: string;
  top: number;
  left: number;
  width: number;
  height: number;
}

/** The first match for `id` that has a box on screen. */
export function findTourTarget(id: string): HTMLElement | null {
  const matches = document.querySelectorAll<HTMLElement>(
    `[data-tour="${CSS.escape(id)}"]`,
  );
  for (const el of matches) {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) return el;
  }
  return null;
}

function measure(ids: string[]): TargetBox[] {
  const boxes: TargetBox[] = [];
  for (const id of ids) {
    const el = findTourTarget(id);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    boxes.push({
      id,
      top: Math.round(r.top),
      left: Math.round(r.left),
      width: Math.round(r.width),
      height: Math.round(r.height),
    });
  }
  return boxes;
}

const sameBoxes = (a: TargetBox[], b: TargetBox[]) =>
  a.length === b.length &&
  a.every(
    (box, i) =>
      box.id === b[i].id &&
      box.top === b[i].top &&
      box.left === b[i].left &&
      box.width === b[i].width &&
      box.height === b[i].height,
  );

export function useTourTargets(ids: string[]): TargetBox[] {
  const key = ids.join(",");
  const [boxes, setBoxes] = useState<TargetBox[]>([]);

  useEffect(() => {
    const list = key ? key.split(",") : [];
    if (list.length === 0) {
      setBoxes([]);
      return;
    }
    let frame = 0;
    let last: TargetBox[] = [];
    const tick = () => {
      const next = measure(list);
      if (!sameBoxes(last, next)) {
        last = next;
        setBoxes(next);
      }
      frame = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(frame);
  }, [key]);

  return boxes;
}
