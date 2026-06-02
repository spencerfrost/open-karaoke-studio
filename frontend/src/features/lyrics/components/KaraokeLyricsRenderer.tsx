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

import React, {
  useMemo,
  useRef,
  useLayoutEffect,
  useState,
  useCallback,
} from "react";
import type { ParsedLrcData } from "@/utils/lrcUtils";
import { getActiveLineIndex } from "./activeLineTiming";

interface CountInStyleConfig {
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
    showProgressBar = false,
    showLeadInHighlight = false,
  } = countInStyle;

  const INSTRUMENTAL_PROGRESS_WIDTH_CLASS = "w-52 sm:w-72";

  const currentTimeMs = currentTime * 1000 + lyricsOffset;
  const currentTimeSec = currentTimeMs / 1000;

  // Refs for scrolling
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<(HTMLDivElement | null)[]>([]);

  // User scroll detection - temporarily disable auto-scroll when user scrolls manually
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const userScrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const lastAutoScrollTimeRef = useRef<number>(0);

  // Reset scroll position and user scroll state when lyrics change (new song)
  useLayoutEffect(() => {
    // Reset user scrolling state
    setIsUserScrolling(false);
    if (userScrollTimeoutRef.current) {
      clearTimeout(userScrollTimeoutRef.current);
      userScrollTimeoutRef.current = null;
    }

    // Reset scroll position to top
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }

    // Reset line refs array for new lyrics
    lineRefs.current = [];
  }, [parsedData]);

  // Handle user scroll - detect manual scrolling and temporarily disable auto-scroll
  const handleScroll = useCallback(() => {
    // If this scroll happened very recently after an auto-scroll, ignore it
    const timeSinceAutoScroll = Date.now() - lastAutoScrollTimeRef.current;
    if (timeSinceAutoScroll < 100) {
      return;
    }

    // User is scrolling manually
    setIsUserScrolling(true);

    // Clear any existing timeout
    if (userScrollTimeoutRef.current) {
      clearTimeout(userScrollTimeoutRef.current);
    }

    // Re-enable auto-scroll after 3 seconds of no user scrolling
    userScrollTimeoutRef.current = setTimeout(() => {
      setIsUserScrolling(false);
    }, 3000);
  }, []);

  // Find current line index (across ALL lines, including blanks)
  const currentLineIndex = useMemo(() => {
    return getActiveLineIndex(parsedData.lines, currentTimeMs);
  }, [parsedData.lines, currentTimeMs]);

  // Find current word index within the active line (null when no alignment data)
  const currentWordIndex = useMemo(() => {
    if (currentLineIndex === -1) return null;
    const activeLine = parsedData.lines[currentLineIndex];
    if (!activeLine?.words || activeLine.words.length === 0) return null;

    const currentTimeSec = currentTimeMs / 1000;
    let idx = -1;
    for (let i = 0; i < activeLine.words.length; i++) {
      if (currentTimeSec >= activeLine.words[i].start) {
        idx = i;
      } else {
        break;
      }
    }
    return idx;
  }, [parsedData.lines, currentLineIndex, currentTimeMs]);

  // Find active count-in trigger
  const activeCountInTrigger = useMemo(() => {
    return parsedData.countInTriggers.find(
      (trigger) =>
        currentTimeMs >= trigger.countInStart &&
        currentTimeMs < trigger.countInEnd,
    );
  }, [parsedData.countInTriggers, currentTimeMs]);

  const activeInstrumentalDisplay = useMemo(() => {
    const interval = parsedData.instrumentalIntervals?.find((candidate) => {
      const leadInStart = Math.min(candidate.lead_in_start, candidate.start);
      return currentTimeSec >= leadInStart && currentTimeSec < candidate.end;
    });

    if (!interval) return null;

    const isLeadIn = currentTimeSec < interval.start;
    return {
      interval,
      isLeadIn,
    };
  }, [parsedData.instrumentalIntervals, currentTimeSec]);

  const activeInstrumentalTargetLineIndex = useMemo(() => {
    if (!activeInstrumentalDisplay) return null;

    const backendLineIndex = activeInstrumentalDisplay.interval.next_line_index;
    const sourceLineMatchIndex = parsedData.lines.findIndex(
      (line) => line.sourceLineIndex === backendLineIndex,
    );

    if (sourceLineMatchIndex !== -1) {
      return sourceLineMatchIndex;
    }

    if (backendLineIndex >= 0 && backendLineIndex < parsedData.lines.length) {
      return backendLineIndex;
    }

    return null;
  }, [activeInstrumentalDisplay, parsedData.lines]);

  // Calculate count-in progress and beat index
  const countInState = useMemo(() => {
    if (activeInstrumentalDisplay) {
      const intervalStart = activeInstrumentalDisplay.isLeadIn
        ? Math.min(
            activeInstrumentalDisplay.interval.lead_in_start,
            activeInstrumentalDisplay.interval.start,
          )
        : activeInstrumentalDisplay.interval.start;
      const intervalEnd = activeInstrumentalDisplay.isLeadIn
        ? activeInstrumentalDisplay.interval.start
        : activeInstrumentalDisplay.interval.end;
      const elapsed = currentTimeSec - intervalStart;
      const duration = Math.max(0.001, intervalEnd - intervalStart);
      const progress = Math.max(0, Math.min(1, elapsed / duration));

      return {
        progress,
        currentBeatIndex: -1,
      };
    }

    if (!activeCountInTrigger) return null;

    const elapsed = currentTimeMs - activeCountInTrigger.countInStart;
    const duration =
      activeCountInTrigger.countInEnd - activeCountInTrigger.countInStart;
    const progress = Math.max(0, Math.min(1, elapsed / duration));
    const currentBeatIndex = Math.floor(
      elapsed / activeCountInTrigger.beatInterval,
    );

    return {
      progress,
      currentBeatIndex,
    };
  }, [activeCountInTrigger, activeInstrumentalDisplay, currentTimeMs, currentTimeSec]);

  // Auto-scroll to center the active line
  useLayoutEffect(() => {
    // Skip auto-scroll if user is manually scrolling
    if (isUserScrolling) return;
    if (currentLineIndex === -1 || !containerRef.current) return;

    const lineElement = lineRefs.current[currentLineIndex];
    if (!lineElement) return;

    const container = containerRef.current;
    const lineOffsetTop = lineElement.offsetTop;
    const lineHeight = lineElement.clientHeight;
    const containerHeight = container.clientHeight;

    // Scroll to center the line: lineTop - containerHeight/2 + lineHeight/2
    const targetScrollTop =
      lineOffsetTop - containerHeight / 2 + lineHeight / 2;

    // Mark this as an auto-scroll to avoid triggering user scroll detection
    lastAutoScrollTimeRef.current = Date.now();

    // Use scrollTo with smooth behavior for smooth scrolling
    container.scrollTo({
      top: targetScrollTop,
      behavior: "smooth",
    });
  }, [currentLineIndex, isUserScrolling]);

  // Recalculate scroll positions on resize
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      // Skip if user is scrolling
      if (isUserScrolling) return;

      // Trigger re-scroll by forcing the scroll effect to run
      if (currentLineIndex !== -1 && containerRef.current) {
        const lineElement = lineRefs.current[currentLineIndex];
        if (lineElement) {
          const container = containerRef.current;
          const lineOffsetTop = lineElement.offsetTop;
          const lineHeight = lineElement.clientHeight;
          const containerHeight = container.clientHeight;
          const targetScrollTop =
            lineOffsetTop - containerHeight / 2 + lineHeight / 2;

          // Mark as auto-scroll
          lastAutoScrollTimeRef.current = Date.now();

          // Use instant scroll on resize to avoid jarring animation
          container.scrollTo({
            top: targetScrollTop,
            behavior: "instant",
          });
        }
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [currentLineIndex, isUserScrolling]);

  // Cleanup timeout on unmount
  useLayoutEffect(() => {
    return () => {
      if (userScrollTimeoutRef.current) {
        clearTimeout(userScrollTimeoutRef.current);
      }
    };
  }, []);

  // Font size configurations
  const fontSizes = useMemo(() => {
    switch (lyricsSize) {
      case "small":
        return {
          inactive: "text-base",
          active: "text-lg",
        };
      case "large":
        return {
          inactive: "text-2xl",
          active: "text-4xl",
        };
      default: // medium
        return {
          inactive: "text-xl",
          active: "text-2xl",
        };
    }
  }, [lyricsSize]);

  // Render all lyrics lines (including blanks)
  const renderAllLines = () => {
    const isClickable = !!onSeek;

    return parsedData.lines.flatMap((line, index) => {
      const renderedElements: React.ReactNode[] = [];
      const isActive = index === currentLineIndex;
      const hasCountIn = activeCountInTrigger?.lineIndex === index;
      const showsInstrumentalSeparator =
        !!activeInstrumentalDisplay &&
        activeInstrumentalTargetLineIndex === index &&
        !!countInState &&
        showProgressBar;

      if (showsInstrumentalSeparator) {
        const separatorStateClass = activeInstrumentalDisplay.isLeadIn
          ? "bg-slate-300/15"
          : "bg-orange-peel/15";
        const progressFillClass = activeInstrumentalDisplay.isLeadIn
          ? "from-slate-200 to-amber-400"
          : "from-orange-peel to-amber-500";
        const progressAriaLabel = activeInstrumentalDisplay.isLeadIn
          ? "Lead-in progress"
          : "Instrumental progress";

        renderedElements.push(
          <div
            key={`instrumental-separator-${activeInstrumentalDisplay.interval.start}-${index}`}
            className="py-2 px-4"
          >
            <div className="w-full flex justify-center">
              <div
                className={`h-2 rounded-full overflow-hidden backdrop-blur-sm ${INSTRUMENTAL_PROGRESS_WIDTH_CLASS} ${separatorStateClass}`}
                role="progressbar"
                aria-label={progressAriaLabel}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(countInState.progress * 100)}
              >
                <div
                  className={`h-full rounded-full instrumental-progress-fill bg-gradient-to-r ${progressFillClass} ${
                    activeInstrumentalDisplay.isLeadIn && showLeadInHighlight
                      ? "instrumental-progress-leadin"
                      : ""
                  }`}
                  style={{ width: `${countInState.progress * 100}%` }}
                />
              </div>
            </div>
          </div>,
        );
      }

      // Check if this line is blank
      if (line.isBlank) {
        renderedElements.push(
          <div
            key={`line-${line.timestamp}-${index}`}
            ref={(el) => {
              lineRefs.current[index] = el;
            }}
            className="py-2 px-4 text-center min-h-[1em]"
          >
            {/* Empty blank line */}
          </div>,
        );

        return renderedElements;
      }

      const fontSize = isActive ? fontSizes.active : fontSizes.inactive;
      const opacity = isActive ? "opacity-100" : "opacity-50";
      const weight = isActive ? "font-bold" : "font-normal";
      const shadow = isActive ? "text-shadow" : "";

      renderedElements.push(
        <div
          key={`line-${line.timestamp}-${index}`}
          ref={(el) => {
            lineRefs.current[index] = el;
          }}
          className={`py-2 px-4 transition-all duration-500 ${fontSize} ${weight} ${shadow} text-background`}
          role={isActive ? "status" : undefined}
          aria-live={isActive ? "polite" : undefined}
        >
          {/* Vertical layout: count-in above text */}
          <div className="flex flex-col items-center justify-center gap-2 w-full">
            {/* Top row: Count-in elements, rendered before the text so it appears as a separate line */}
            {hasCountIn && countInState && (
              <div className={`flex items-center justify-center gap-3 ${opacity}`}>
                {showProgressBar && (
                  <div className="w-32 h-1.5 bg-white/20 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-orange-peel to-amber-500 rounded-full transition-all duration-100 ease-linear"
                      style={{ width: `${countInState.progress * 100}%` }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Bottom row: Lyrics text */}
            <div className="text-center">
              {isActive && line.words && line.words.length > 0 ? (
                <span
                  className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100" : ""}`}
                  onClick={
                    isClickable
                      ? () => onSeek?.(line.timestamp / 1000)
                      : undefined
                  }
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
                  {line.words.map((w, wIdx) => (
                    <span
                      key={wIdx}
                      className={`transition-all duration-100 ${
                        currentWordIndex !== null && wIdx <= currentWordIndex
                          ? "opacity-100 text-orange-peel"
                          : "opacity-60"
                      }`}
                    >
                      {w.word}
                      {wIdx < line.words!.length - 1 ? " " : ""}
                    </span>
                  ))}
                </span>
              ) : (
                <span
                  className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100 inline-block" : ""}`}
                  onClick={
                    isClickable
                      ? () => onSeek?.(line.timestamp / 1000)
                      : undefined
                  }
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
              )}
            </div>
          </div>
        </div>,
      );

      return renderedElements;
    });
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-y-auto scrollbar-hide flex flex-col ${className}`}
      onScroll={handleScroll}
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
