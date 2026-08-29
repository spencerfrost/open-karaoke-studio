/**
 * useLyricsOffsetDrag - drag a readout up/down to nudge a numeric value.
 *
 * Lifted from the old settings-menu LyricsTimingView, which handled mouse and
 * touch with correct global-listener cleanup. Behaviour is unchanged: drag up
 * is positive, one pixel is one step.
 */

import React, { useCallback, useState } from "react";

interface UseLyricsOffsetDragOptions {
  value: number;
  onChange: (value: number) => void;
  /** Value change per drag step. */
  step?: number;
  /** Pixels of travel per step. */
  sensitivity?: number;
}

interface UseLyricsOffsetDragResult {
  isDragging: boolean;
  /** Spread onto the draggable readout element. */
  dragHandleProps: {
    onMouseDown: (e: React.MouseEvent) => void;
    onTouchStart: (e: React.TouchEvent) => void;
  };
}

export const useLyricsOffsetDrag = ({
  value,
  onChange,
  step = 100,
  sensitivity = 1,
}: UseLyricsOffsetDragOptions): UseLyricsOffsetDragResult => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [dragStartValue, setDragStartValue] = useState(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      setDragStartY(e.clientY);
      setDragStartValue(value);
      document.body.style.cursor = "ns-resize";
    },
    [value],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      e.preventDefault();
      const deltaY = dragStartY - e.clientY; // Drag up = positive
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = dragStartValue + deltaSteps * step;
      if (newValue !== value) {
        onChange(newValue);
      }
    },
    [
      isDragging,
      dragStartY,
      dragStartValue,
      value,
      onChange,
      step,
      sensitivity,
    ],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = "auto";
  }, []);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      setIsDragging(true);
      setDragStartY(touch.clientY);
      setDragStartValue(value);
    },
    [value],
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!isDragging) return;
      e.preventDefault();
      const touch = e.touches[0];
      const deltaY = dragStartY - touch.clientY;
      const deltaSteps = Math.round(deltaY / sensitivity);
      const newValue = dragStartValue + deltaSteps * step;
      if (newValue !== value) {
        onChange(newValue);
      }
    },
    [
      isDragging,
      dragStartY,
      dragStartValue,
      value,
      onChange,
      step,
      sensitivity,
    ],
  );

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global event listeners for drag - CRITICAL cleanup
  React.useEffect(() => {
    if (!isDragging) return;

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("touchmove", handleTouchMove, { passive: false });
    document.addEventListener("touchend", handleTouchEnd);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleTouchEnd);
    };
  }, [
    isDragging,
    handleMouseMove,
    handleMouseUp,
    handleTouchMove,
    handleTouchEnd,
  ]);

  return {
    isDragging,
    dragHandleProps: {
      onMouseDown: handleMouseDown,
      onTouchStart: handleTouchStart,
    },
  };
};
