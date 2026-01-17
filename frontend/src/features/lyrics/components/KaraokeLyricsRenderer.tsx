/**
 * KaraokeLyricsRenderer - Custom LRC renderer with integrated count-in support
 * Replaces react-lrc with native implementation optimized for karaoke display
 *
 * Features:
 * - Full lyrics list display with smooth auto-scrolling
 * - Vertical centering for all lines (including first/last)
 * - Count-in overlay during instrumental gaps
 * - Responsive sizing and animations
 */

import React, { useMemo, useRef, useLayoutEffect } from "react";
import type { ParsedLrcData } from "@/utils/lrcUtils";

interface CountInStyleConfig {
  showCountdownNumbers?: boolean;
  showCountdownIcons?: boolean;
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;
}

interface KaraokeLyricsRendererProps {
  parsedData: ParsedLrcData;
  currentTime: number; // seconds
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number; // milliseconds
  bpm?: number;
  countInStyle?: CountInStyleConfig;
  onSeek?: (timeSeconds: number) => void;
  className?: string;
}

const KaraokeLyricsRenderer: React.FC<KaraokeLyricsRendererProps> = ({
  parsedData,
  currentTime,
  lyricsSize,
  lyricsOffset,
  countInStyle = {},
  onSeek,
  className = "",
}) => {
  const {
    showCountdownNumbers = false,
    showCountdownIcons = false,
    showProgressBar = false,
  } = countInStyle;

  const currentTimeMs = currentTime * 1000 + lyricsOffset;

  // Refs for scrolling
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Find current line index (across ALL lines, including blanks)
  const currentLineIndex = useMemo(() => {
    let idx = parsedData.lines.findIndex(
      (line, i) => {
        const nextLine = parsedData.lines[i + 1];
        return (
          currentTimeMs >= line.timestamp &&
          (!nextLine || currentTimeMs < nextLine.timestamp)
        );
      }
    );

    // If no current line found, check if we're before first line
    if (idx === -1) {
      idx = currentTimeMs < parsedData.lines[0]?.timestamp ? -1 : parsedData.lines.length - 1;
    }

    return idx;
  }, [parsedData.lines, currentTimeMs]);

  // Find active count-in trigger
  const activeCountInTrigger = useMemo(() => {
    return parsedData.countInTriggers.find(
      (trigger) => currentTimeMs >= trigger.countInStart && currentTimeMs < trigger.countInEnd
    );
  }, [parsedData.countInTriggers, currentTimeMs]);

  // Calculate count-in progress and beat index
  const countInState = useMemo(() => {
    if (!activeCountInTrigger) return null;

    const elapsed = currentTimeMs - activeCountInTrigger.countInStart;
    const duration = activeCountInTrigger.countInEnd - activeCountInTrigger.countInStart;
    const progress = Math.max(0, Math.min(1, elapsed / duration));
    const currentBeatIndex = Math.floor(elapsed / activeCountInTrigger.beatInterval);

    return {
      progress,
      currentBeatIndex,
      trigger: activeCountInTrigger,
    };
  }, [activeCountInTrigger, currentTimeMs]);

  // Auto-scroll to center the active line
  useLayoutEffect(() => {
    if (currentLineIndex === -1 || !containerRef.current) return;

    const lineElement = lineRefs.current[currentLineIndex];
    if (!lineElement) return;

    const container = containerRef.current;
    const lineOffsetTop = lineElement.offsetTop;
    const lineHeight = lineElement.clientHeight;
    const containerHeight = container.clientHeight;

    // Scroll to center the line: lineTop - containerHeight/2 + lineHeight/2
    const targetScrollTop = lineOffsetTop - containerHeight / 2 + lineHeight / 2;
    container.scrollTop = targetScrollTop;
  }, [currentLineIndex]);

  // Recalculate scroll positions on resize
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      // Trigger re-scroll by forcing the scroll effect to run
      if (currentLineIndex !== -1 && containerRef.current) {
        const lineElement = lineRefs.current[currentLineIndex];
        if (lineElement) {
          const container = containerRef.current;
          const lineOffsetTop = lineElement.offsetTop;
          const lineHeight = lineElement.clientHeight;
          const containerHeight = container.clientHeight;
          const targetScrollTop = lineOffsetTop - containerHeight / 2 + lineHeight / 2;
          container.scrollTop = targetScrollTop;
        }
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [currentLineIndex]);

  // Font size configurations
  const fontSizes = useMemo(() => {
    switch (lyricsSize) {
      case "small":
        return {
          inactive: "text-base",
          active: "text-lg",
          countdown: "text-lg",
          icon: "w-2 h-2",
        };
      case "large":
        return {
          inactive: "text-2xl",
          active: "text-4xl",
          countdown: "text-3xl",
          icon: "w-4 h-4",
        };
      default: // medium
        return {
          inactive: "text-xl",
          active: "text-2xl",
          countdown: "text-2xl",
          icon: "w-3 h-3",
        };
    }
  }, [lyricsSize]);

  // Render all lyrics lines (including blanks)
  const renderAllLines = () => {
    const isClickable = !!onSeek;

    return parsedData.lines.map((line, index) => {
      const isActive = index === currentLineIndex;
      const hasCountIn = activeCountInTrigger?.lineIndex === index;

      // Check if this line is blank
      if (line.isBlank) {
        return (
          <div
            key={line.timestamp}
            ref={(el) => { lineRefs.current[index] = el; }}
            className="py-2 px-4 text-center min-h-[1em]"
          >
            {/* Empty blank line */}
          </div>
        );
      }

      const fontSize = isActive ? fontSizes.active : fontSizes.inactive;
      const opacity = isActive ? "opacity-100" : "opacity-50";
      const weight = isActive ? "font-bold" : "font-normal";
      const shadow = isActive ? "text-shadow" : "";

      return (
        <div
          key={line.timestamp}
          ref={(el) => { lineRefs.current[index] = el; }}
          className={`py-2 px-4 transition-all duration-500 ${fontSize} ${weight} ${shadow} text-background`}
          role={isActive ? "status" : undefined}
          aria-live={isActive ? "polite" : undefined}
        >
          {/* 3-column grid: left for count-in, center for text, right for balance */}
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 w-full">
            {/* Left column: Count-in elements */}
            <div className={`flex items-center justify-end gap-3 ${opacity}`}>
              {hasCountIn && countInState && (
                <>
                  {/* Progress bar */}
                  {showProgressBar && (
                    <div className="w-32 h-1.5 bg-white/20 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-orange-peel to-amber-500 rounded-full transition-all duration-100 ease-linear"
                        style={{ width: `${countInState.progress * 100}%` }}
                      />
                    </div>
                  )}

                  {/* Countdown numbers */}
                  {showCountdownNumbers && (
                    <div className="flex gap-2">
                      {[4, 3, 2, 1].map((num, idx) => (
                        <span
                          key={num}
                          className={`
                            font-bold transition-all duration-150
                            ${fontSizes.countdown}
                            ${idx === countInState.currentBeatIndex
                              ? "text-orange-peel scale-110 opacity-100"
                              : "text-white/30 scale-100 opacity-50"
                            }
                          `}
                        >
                          {num}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Countdown icons */}
                  {showCountdownIcons && (
                    <div className="flex gap-2 items-center">
                      {[0, 1, 2, 3].map((idx) => (
                        <div
                          key={idx}
                          className={`
                            rounded-full transition-all duration-100
                            ${fontSizes.icon}
                            ${idx <= countInState.currentBeatIndex
                              ? "bg-transparent border-2 border-white/30"
                              : "bg-orange-peel"
                            }
                          `}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Center column: Centered text */}
            <div className="text-center">
              <span
                className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100 inline-block" : ""}`}
                onClick={isClickable ? () => onSeek?.(line.timestamp / 1000) : undefined}
                role={isClickable ? "button" : undefined}
                tabIndex={isClickable ? 0 : undefined}
                onKeyDown={
                  isClickable
                    ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSeek?.(line.timestamp / 1000);
                      }
                    }
                    : undefined
                }
              >
                {line.content}
              </span>
            </div>

            {/* Right column: Empty for balance */}
            <div />
          </div>

        </div>
      );
    });
  };


  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-y-auto scroll-smooth scrollbar-hide ${className}`}
    >
      {/* Top spacer for vertical centering */}
      <div className="flex-1 min-h-[50vh]" />

      {/* All lyrics lines */}
      {renderAllLines()}

      {/* Bottom spacer for vertical centering */}
      <div className="flex-1 min-h-[50vh]" />
    </div>
  );
};

export default React.memo(KaraokeLyricsRenderer);
