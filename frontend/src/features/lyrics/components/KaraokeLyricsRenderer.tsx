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

type ParsedLine = ParsedLrcData["lines"][number];
type InstrumentalInterval = NonNullable<
  ParsedLrcData["instrumentalIntervals"]
>[number];

interface SeekableSpanProps {
  onClick?: () => void;
  role?: "button";
  tabIndex?: number;
  onKeyDown?: (e: React.KeyboardEvent<HTMLSpanElement>) => void;
}

export function getInstrumentalSeparatorLineIndex(
  lines: ParsedLine[],
  targetLineIndex: number | null,
): number | null {
  if (
    targetLineIndex === null ||
    targetLineIndex < 0 ||
    targetLineIndex >= lines.length
  ) {
    return null;
  }

  let separatorLineIndex = targetLineIndex;

  while (separatorLineIndex > 0 && lines[separatorLineIndex - 1]?.isBlank) {
    separatorLineIndex -= 1;
  }

  return separatorLineIndex;
}

export function getInstrumentalTargetLineIndex(
  lines: ParsedLine[],
  interval: InstrumentalInterval,
): number | null {
  if (lines.length === 0) return null;

  const intervalEndMs = interval.end * 1000;
  const TIMESTAMP_EPSILON_MS = 25;
  const intervalEndSec = interval.end;
  const WORD_EPSILON_SEC = 0.03;

  // Primary strategy: use attached alignment words when available.
  // This keeps instrumental placement tied to the same timing source as the
  // interval itself, even if LRC timestamps/indexes drift.
  let wordMatchedIndex: number | null = null;
  let earliestStartAtOrAfterEnd = Number.POSITIVE_INFINITY;

  for (let i = 0; i < lines.length; i++) {
    const words = lines[i].words;
    if (!words || words.length === 0) continue;

    const firstWordStart = words.reduce(
      (minStart, word) => Math.min(minStart, word.start),
      Number.POSITIVE_INFINITY,
    );

    if (firstWordStart >= intervalEndSec - WORD_EPSILON_SEC) {
      if (firstWordStart < earliestStartAtOrAfterEnd) {
        earliestStartAtOrAfterEnd = firstWordStart;
        wordMatchedIndex = i;
      }
    }
  }

  if (wordMatchedIndex !== null) {
    return wordMatchedIndex;
  }

  // Prefer timestamp matching first because it is stable even when backend
  // line indexes use a different namespace (content-only vs raw source lines).
  const exactOrAfterByTime = lines.findIndex(
    (line) => line.timestamp >= intervalEndMs - TIMESTAMP_EPSILON_MS,
  );
  if (exactOrAfterByTime !== -1) {
    return exactOrAfterByTime;
  }

  const sourceLineMatchIndex = lines.findIndex(
    (line) => line.sourceLineIndex === interval.next_line_index,
  );
  if (sourceLineMatchIndex !== -1) {
    return sourceLineMatchIndex;
  }

  if (interval.next_line_index >= 0 && interval.next_line_index < lines.length) {
    return interval.next_line_index;
  }

  return null;
}

interface InstrumentalProgressState {
  progress: number;
  isLeadIn: boolean;
  isActiveWindow: boolean;
}

export function getInstrumentalProgressState(
  interval: InstrumentalInterval,
  currentTimeSec: number,
): InstrumentalProgressState {
  const leadInStart = Math.min(interval.lead_in_start, interval.start);

  if (currentTimeSec <= leadInStart) {
    return {
      progress: 0,
      isLeadIn: true,
      isActiveWindow: false,
    };
  }

  if (currentTimeSec >= interval.end) {
    return {
      progress: 1,
      isLeadIn: false,
      isActiveWindow: false,
    };
  }

  if (currentTimeSec < interval.start) {
    return {
      progress: getProgress(
        currentTimeSec - leadInStart,
        Math.max(0.001, interval.start - leadInStart),
      ),
      isLeadIn: true,
      isActiveWindow: true,
    };
  }

  return {
    progress: getProgress(
      currentTimeSec - interval.start,
      Math.max(0.001, interval.end - interval.start),
    ),
    isLeadIn: false,
    isActiveWindow: true,
  };
}

function getCenteredScrollTop(
  container: HTMLDivElement,
  lineElement: HTMLDivElement,
): number {
  return (
    lineElement.offsetTop - container.clientHeight / 2 + lineElement.clientHeight / 2
  );
}

function getProgress(elapsed: number, duration: number): number {
  return Math.max(0, Math.min(1, elapsed / duration));
}

interface InstrumentalSeparatorProps {
  isLeadIn: boolean;
  progress: number;
  showLeadInHighlight: boolean;
  widthClass: string;
}

const InstrumentalSeparator: React.FC<InstrumentalSeparatorProps> = ({
  isLeadIn,
  progress,
  showLeadInHighlight,
  widthClass,
}) => {
  const separatorStateClass = isLeadIn ? "bg-slate-300/15" : "bg-orange-peel/15";
  const progressFillClass = isLeadIn
    ? "from-slate-200 to-amber-400"
    : "from-orange-peel to-amber-500";
  const progressAriaLabel = isLeadIn ? "Lead-in progress" : "Instrumental progress";

  return (
    <div className="py-2 px-4">
      <div className="w-full flex justify-center">
        <div
          className={`h-2 rounded-full overflow-hidden backdrop-blur-sm ${widthClass} ${separatorStateClass}`}
          role="progressbar"
          aria-label={progressAriaLabel}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
        >
          <div
            className={`h-full rounded-full instrumental-progress-fill bg-gradient-to-r ${progressFillClass} ${
              isLeadIn && showLeadInHighlight ? "instrumental-progress-leadin" : ""
            }`}
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

interface LyricContentProps {
  line: ParsedLine;
  renderMode: "content" | "words";
  isActive: boolean;
  opacity: string;
  isClickable: boolean;
  seekProps: SeekableSpanProps;
  currentWordIndex: number | null;
}

const LyricContent: React.FC<LyricContentProps> = ({
  line,
  renderMode,
  isActive,
  opacity,
  isClickable,
  seekProps,
  currentWordIndex,
}) => {
  if (renderMode === "words") {
    const words =
      line.words && line.words.length > 0
        ? line.words.map((w) => w.word)
        : line.content.split(/\s+/).filter(Boolean);

    if (words.length === 0) {
      return (
        <span
          className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100 inline-block" : ""}`}
          {...seekProps}
        >
          {line.content}
        </span>
      );
    }

    return (
      <span
        className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100" : ""}`}
        {...seekProps}
      >
        {words.map((word, wIdx) => (
          <span
            key={wIdx}
            className={`transition-all duration-100 ${
              isActive && currentWordIndex !== null && wIdx <= currentWordIndex
                ? "opacity-100 text-orange-peel"
                : "opacity-60"
            }`}
          >
            {word}
            {wIdx < words.length - 1 ? " " : ""}
          </span>
        ))}
      </span>
    );
  }

  return (
    <span
      className={`${opacity} transition-all duration-500 ${isClickable ? "cursor-pointer hover:opacity-100 inline-block" : ""}`}
      {...seekProps}
    >
      {line.content}
    </span>
  );
};

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

  const scrollActiveLine = useCallback(
    (behavior: ScrollBehavior) => {
      if (isUserScrolling || currentLineIndex === -1 || !containerRef.current)
        return;

      const lineElement = lineRefs.current[currentLineIndex];
      if (!lineElement) return;

      lastAutoScrollTimeRef.current = Date.now();
      containerRef.current.scrollTo({
        top: getCenteredScrollTop(containerRef.current, lineElement),
        behavior,
      });
    },
    [currentLineIndex, isUserScrolling],
  );

  // Find current word index within the active line (null when no alignment data)
  const currentWordIndex = useMemo(() => {
    if (currentLineIndex === -1) return null;
    const activeLine = parsedData.lines[currentLineIndex];
    if (!activeLine?.words || activeLine.words.length === 0) return null;

    let idx = -1;
    for (let i = 0; i < activeLine.words.length; i++) {
      if (currentTimeSec >= activeLine.words[i].start) {
        idx = i;
      } else {
        break;
      }
    }
    return idx;
  }, [parsedData.lines, currentLineIndex, currentTimeSec]);

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

    return getInstrumentalTargetLineIndex(
      parsedData.lines,
      activeInstrumentalDisplay.interval,
    );
  }, [activeInstrumentalDisplay, parsedData.lines]);

  const activeInstrumentalSeparatorLineIndex = useMemo(() => {
    return getInstrumentalSeparatorLineIndex(
      parsedData.lines,
      activeInstrumentalTargetLineIndex,
    );
  }, [activeInstrumentalTargetLineIndex, parsedData.lines]);

  const instrumentalSeparatorsByLine = useMemo(() => {
    const byLine = new Map<number, InstrumentalInterval[]>();

    for (const interval of parsedData.instrumentalIntervals ?? []) {
      const targetLineIndex = getInstrumentalTargetLineIndex(parsedData.lines, interval);
      const separatorLineIndex = getInstrumentalSeparatorLineIndex(
        parsedData.lines,
        targetLineIndex,
      );

      if (separatorLineIndex === null) continue;

      const existing = byLine.get(separatorLineIndex) ?? [];
      existing.push(interval);
      byLine.set(separatorLineIndex, existing);
    }

    return byLine;
  }, [parsedData.instrumentalIntervals, parsedData.lines]);

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
      const progress = getProgress(elapsed, duration);

      return {
        progress,
        currentBeatIndex: -1,
      };
    }

    if (!activeCountInTrigger) return null;

    const elapsed = currentTimeMs - activeCountInTrigger.countInStart;
    const duration =
      activeCountInTrigger.countInEnd - activeCountInTrigger.countInStart;
    const progress = getProgress(elapsed, duration);
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
    scrollActiveLine("smooth");
  }, [scrollActiveLine]);

  // Recalculate scroll positions on resize
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      scrollActiveLine("instant");
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [scrollActiveLine]);

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
    const hasAnyWordTiming = parsedData.lines.some(
      (line) => !line.isBlank && !!line.words && line.words.length > 0,
    );
    const renderMode: "content" | "words" = hasAnyWordTiming
      ? "words"
      : "content";

    const getSeekProps = (lineTimestampMs: number): SeekableSpanProps => {
      if (!isClickable) {
        return {
          onClick: undefined,
          role: undefined,
          tabIndex: undefined,
          onKeyDown: undefined,
        };
      }

      const seekTo = lineTimestampMs / 1000;

      return {
        onClick: () => onSeek?.(seekTo),
        role: "button" as const,
        tabIndex: 0,
        onKeyDown: (e: React.KeyboardEvent<HTMLSpanElement>) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSeek?.(seekTo);
          }
        },
      };
    };

    return parsedData.lines.flatMap((line, index) => {
      const renderedElements: React.ReactNode[] = [];
      const isActive = index === currentLineIndex;
      const hasCountIn = activeCountInTrigger?.lineIndex === index;
      const lineInstrumentalIntervals = instrumentalSeparatorsByLine.get(index) ?? [];

      if (showProgressBar && lineInstrumentalIntervals.length > 0) {
        for (const interval of lineInstrumentalIntervals) {
          const progressState = getInstrumentalProgressState(interval, currentTimeSec);
          const isResolvedActiveInterval =
            !!activeInstrumentalDisplay &&
            activeInstrumentalDisplay.interval.start === interval.start &&
            activeInstrumentalDisplay.interval.end === interval.end &&
            activeInstrumentalSeparatorLineIndex === index;

          renderedElements.push(
            <InstrumentalSeparator
              key={`instrumental-separator-${interval.start}-${interval.end}-${index}`}
              isLeadIn={progressState.isLeadIn}
              progress={progressState.progress}
              showLeadInHighlight={
                showLeadInHighlight &&
                progressState.isActiveWindow &&
                isResolvedActiveInterval
              }
              widthClass={INSTRUMENTAL_PROGRESS_WIDTH_CLASS}
            />,
          );
        }
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
      const seekProps = getSeekProps(line.timestamp);

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
              <LyricContent
                line={line}
                renderMode={renderMode}
                isActive={isActive}
                opacity={opacity}
                isClickable={isClickable}
                seekProps={seekProps}
                currentWordIndex={currentWordIndex}
              />
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
