/**
 * WheelColumn - one column of the song wheel: a list that slides to keep the
 * cursor in the middle, DDR style, but stops at its ends so the top and bottom
 * of the list sit flush with the column instead of leaving empty space. Near
 * an end the cursor (and its glow) moves off the middle instead.
 *
 * Only the rows near what is on screen exist. The rows are positioned in list
 * coordinates on a strip, and the strip slides, so a row mounted at the edge
 * slides into view like any other. ~17 rows per column rather than 600 is
 * what makes the wheel cheap to mount.
 *
 * No surface of its own: text on the stage background, and a soft glow behind
 * the selected row while this column is at the front.
 */

import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { WHEEL_TUNING, listScrollOffset } from "./wheelModel";

/** The column's height, header included. */
const COLUMN_HEIGHT = 660;
/** Rows rendered past each edge of the visible list, so a slide has rows to
 *  bring in. */
const SLIDE_ROOM_ROWS = 3;
/** How much of the list fades out at an end with more list beyond it. */
const EDGE_FADE = "18%";
/** One notch of a line-based wheel, or this many pixels of a smooth one. */
const WHEEL_PIXELS_PER_ROW = 50;

interface WheelColumnProps {
  label: string;
  /** Replaces the plain label - the song column puts the artist's name there. */
  header?: React.ReactNode;
  /** Pixels from the top where the list starts, below the header. */
  listTop: number;
  width: number;
  rowHeight: number;
  count: number;
  cursor: number;
  active: boolean;
  /** 0–1; compounds with distance from the front. */
  brightness: number;
  /** The cylinder placement, from the wheel. */
  transform: string;
  /** How long a turn of the wheel takes; 0 with reduced motion. */
  turnMs: number;
  /** How long a one-row slide takes; 0 with reduced motion. */
  scrollMs: number;
  /** Empty letters: shown dimmer, skipped by the cursor. */
  isRowDisabled?: (index: number) => boolean;
  renderRow: (index: number, isCurrent: boolean) => React.ReactNode;
  rowClassName?: string;
  onActivate: () => void;
  onRowClick: (index: number) => void;
  /** Positive steps move down the list. Brings the column to the front. */
  onWheelSteps: (dir: -1 | 1, steps: number) => void;
  /** Shown instead of rows when there are none yet. */
  placeholder?: React.ReactNode;
}

const WheelColumn: React.FC<WheelColumnProps> = ({
  label,
  header,
  listTop,
  width,
  rowHeight,
  count,
  cursor,
  active,
  brightness,
  transform,
  turnMs,
  scrollMs,
  isRowDisabled,
  renderRow,
  rowClassName,
  onActivate,
  onRowClick,
  onWheelSteps,
  placeholder,
}) => {
  const ref = useRef<HTMLDivElement>(null);

  // Native, because React's onWheel is passive and cannot stop the page
  // scrolling. The scroll wheel spins whichever column the pointer is over and
  // brings it to the front.
  const wheelRef = useRef({ onWheelSteps, acc: 0 });
  wheelRef.current.onWheelSteps = onWheelSteps;
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const w = wheelRef.current;
      const step =
        e.deltaMode === WheelEvent.DOM_DELTA_LINE ? 1 : WHEEL_PIXELS_PER_ROW;
      w.acc += e.deltaY;
      const steps = Math.trunc(w.acc / step);
      if (steps === 0) return;
      w.acc -= steps * step;
      w.onWheelSteps(steps < 0 ? -1 : 1, Math.abs(steps));
    };
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, []);

  const viewportPx = COLUMN_HEIGHT - listTop;
  const offset = listScrollOffset(cursor, count, rowHeight, viewportPx);
  const moreAbove = offset > 0;
  const moreBelow = offset + viewportPx < count * rowHeight;

  const first = Math.max(0, Math.floor(offset / rowHeight) - SLIDE_ROOM_ROWS);
  const last = Math.min(
    count - 1,
    Math.ceil((offset + viewportPx) / rowHeight) + SLIDE_ROOM_ROWS,
  );
  const rows: React.ReactNode[] = [];
  for (let i = first; i <= last; i++) {
    const distance = Math.abs(i - cursor);
    const isCurrent = distance === 0;
    const disabled = isRowDisabled?.(i) ?? false;
    const base = disabled ? 0.55 : 1;
    rows.push(
      <div
        key={i}
        onClick={(e) => {
          e.stopPropagation();
          if (active) onRowClick(i);
          else onActivate();
        }}
        className={cn(
          "absolute inset-x-0 flex items-center overflow-hidden whitespace-nowrap",
          isCurrent ? "font-semibold text-foreground" : "text-foreground/90",
          disabled && "text-foreground/40",
          isCurrent && active && "wheel-row-glow",
          rowClassName,
        )}
        style={{
          top: i * rowHeight,
          height: rowHeight,
          opacity: isCurrent
            ? 1
            : Math.max(0.12, base * (0.8 - distance * 0.1)),
          transition: `opacity ${scrollMs}ms, color ${scrollMs}ms`,
        }}
      >
        {renderRow(i, isCurrent)}
      </div>,
    );
  }

  return (
    <div
      ref={ref}
      onClick={() => {
        if (!active) onActivate();
      }}
      aria-label={label}
      className={cn(
        "absolute overflow-hidden",
        active ? "cursor-default" : "cursor-pointer",
        brightness === 0 && "pointer-events-none",
      )}
      style={{
        top: -COLUMN_HEIGHT / 2,
        height: COLUMN_HEIGHT,
        left: -width / 2,
        width,
        transform,
        opacity: brightness,
        // Same duration and easing as the ring, so the counter-rotation that
        // keeps the text facing forward stays in step with the turn.
        transition: `transform ${turnMs}ms ${WHEEL_TUNING.turnEasing}, opacity ${turnMs}ms`,
      }}
    >
      <div
        className={cn(
          "absolute inset-x-0 top-0 z-[3] truncate px-7 pb-3.5 pt-5 font-display text-lg font-bold uppercase tracking-[0.14em]",
          active ? "text-primary" : "text-foreground/60",
        )}
      >
        {header ?? label}
      </div>

      {/* The list starts below the header so rows do not scroll up behind
          it, and fades out only at an end with more list past it. */}
      <div
        className="wheel-list-mask absolute inset-x-0 bottom-0"
        style={
          {
            top: listTop,
            "--wheel-fade-top": moreAbove ? EDGE_FADE : "0%",
            "--wheel-fade-bottom": moreBelow ? EDGE_FADE : "0%",
            transition: `--wheel-fade-top ${scrollMs}ms, --wheel-fade-bottom ${scrollMs}ms`,
          } as React.CSSProperties
        }
      >
        <div
          aria-hidden
          className="wheel-band pointer-events-none absolute inset-x-2.5 top-0"
          style={{
            height: rowHeight * 1.6,
            opacity: active ? 1 : 0,
            // Centred on the cursor row, wherever the clamp left it.
            transform: `translateY(${cursor * rowHeight - offset - rowHeight * 0.3}px)`,
            transition: `opacity ${turnMs}ms, transform ${scrollMs}ms ${WHEEL_TUNING.turnEasing}`,
          }}
        />
        {count === 0 && placeholder ? (
          <div
            className="absolute inset-x-0 top-0 flex items-center px-7 text-2xl text-foreground/50"
            style={{ height: rowHeight }}
          >
            {placeholder}
          </div>
        ) : (
          <div
            className="absolute inset-x-0 top-0 will-change-transform"
            style={{
              transform: `translateY(${-offset}px)`,
              transition: `transform ${scrollMs}ms ${WHEEL_TUNING.turnEasing}`,
            }}
          >
            {rows}
          </div>
        )}
      </div>
    </div>
  );
};

export default WheelColumn;
