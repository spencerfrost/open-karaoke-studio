/**
 * LRC Parser for Count-In System
 * Parses LRC lyrics to detect blank lines, instrumental gaps, and calculate count-in triggers
 */

export interface WordTimestamp {
  word: string;
  start: number; // seconds
  end: number; // seconds
  score?: number;
  line_index: number; // originating LRC line index
}

export interface LrcLine {
  timestamp: number; // milliseconds
  content: string;
  isBlank: boolean;
  sourceLineIndex: number; // original LRC source line index
  words?: WordTimestamp[]; // word-level timestamps from forced alignment
}

export interface InstrumentalGap {
  startTime: number; // milliseconds
  endTime: number; // milliseconds
  duration: number; // milliseconds
  lineIndexAfter: number; // which line comes after this gap
}

export interface InstrumentalInterval {
  start: number; // seconds
  end: number; // seconds
  duration: number; // seconds
  lead_in_start: number; // seconds
  next_line_index: number;
  confidence: number;
  source: string;
}

export interface CountInTrigger {
  lineIndex: number; // which line to show count-in for
  gapDuration: number; // milliseconds
  countInStart: number; // milliseconds when count-in should start (4 beats before line)
  countInEnd: number; // milliseconds when count-in ends (line starts)
  beatInterval: number; // milliseconds per beat (from BPM)
}

export interface ParsedLrcData {
  lines: LrcLine[];
  gaps: InstrumentalGap[];
  countInTriggers: CountInTrigger[];
  instrumentalIntervals?: InstrumentalInterval[];
}

/**
 * Parse LRC content into structured line data
 */
export function parseLrc(lrcContent: string): LrcLine[] {
  if (!lrcContent) return [];

  const lines: LrcLine[] = [];
  // LRC timestamp format: [mm:ss.xx] or [mm:ss.xxx]
  // Parse line-by-line so sourceLineIndex matches backend indexing behavior.
  const timestampRegex = /^\[(\d{1,2}):(\d{2})\.(\d{2,3})\]\s*(.*)$/;
  const sourceLines = lrcContent.trim().split(/\r?\n/);

  sourceLines.forEach((rawLine, sourceLineIndex) => {
    const match = rawLine.match(timestampRegex);
    if (!match) return;

    const [, minutes, seconds, ms, content] = match;

    // Parse timestamp to milliseconds
    // Handle both 2-digit (centiseconds) and 3-digit (milliseconds) precision
    const msValue = ms.length === 2 ? parseInt(ms) * 10 : parseInt(ms);

    const timestamp =
      parseInt(minutes) * 60000 + parseInt(seconds) * 1000 + msValue;

    lines.push({
      timestamp,
      content: content || "",
      isBlank: !content || content.trim().length === 0,
      sourceLineIndex,
    });
  });

  // Sort by timestamp
  return lines.sort((a, b) => a.timestamp - b.timestamp);
}

/**
 * Find instrumental gaps in parsed LRC lines
 * Detects consecutive blank lines or large time jumps between lines
 */
export function findInstrumentalGaps(
  lines: LrcLine[],
  minGapMs: number = 2000,
): InstrumentalGap[] {
  if (lines.length === 0) return [];

  const gaps: InstrumentalGap[] = [];
  let gapStart: number | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const nextLine = lines[i + 1];

    // Start tracking a gap if we hit a blank line
    if (line.isBlank && gapStart === null) {
      gapStart = i;
    }

    // If we're in a gap and hit a non-blank line, or reach end of file
    if (gapStart !== null && (!line.isBlank || !nextLine)) {
      const gapStartTime = lines[gapStart].timestamp;
      const gapEndTime = !line.isBlank ? line.timestamp : lines[i].timestamp;
      const lineIndexAfter = !line.isBlank ? i : i + 1;

      // Only create gap if it meets minimum duration and has a line after it
      if (lineIndexAfter < lines.length) {
        const duration = gapEndTime - gapStartTime;
        if (duration >= minGapMs) {
          gaps.push({
            startTime: gapStartTime,
            endTime: gapEndTime,
            duration,
            lineIndexAfter,
          });
        }
      }

      gapStart = null;
    }
  }

  return gaps;
}

/**
 * Calculate count-in triggers based on gaps and BPM
 */
export function calculateCountInTriggers(
  lines: LrcLine[],
  gaps: InstrumentalGap[],
  bpm: number | undefined,
  minBeats: number = 4,
): CountInTrigger[] {
  if (!bpm || bpm < 30 || bpm > 300) return [];
  if (lines.length === 0) return [];

  const triggers: CountInTrigger[] = [];
  const beatInterval = 60000 / bpm; // milliseconds per beat
  const minGapDuration = beatInterval * minBeats;

  // Check first line for count-in (if it starts after 3 seconds)
  const firstLine = lines.find((l) => !l.isBlank);
  if (firstLine && firstLine.timestamp > 3000) {
    const countInStart = Math.max(
      0,
      firstLine.timestamp - beatInterval * minBeats,
    );
    const hasEnoughTime = firstLine.timestamp - countInStart >= minGapDuration;

    if (hasEnoughTime) {
      const firstLineIndex = lines.indexOf(firstLine);
      triggers.push({
        lineIndex: firstLineIndex,
        gapDuration: firstLine.timestamp,
        countInStart,
        countInEnd: firstLine.timestamp,
        beatInterval,
      });
    }
  }

  // Process gaps to find lines that need count-in
  for (const gap of gaps) {
    // Skip if gap is too short for count-in
    if (gap.duration < minGapDuration) continue;

    // Skip if line index is out of bounds
    if (gap.lineIndexAfter >= lines.length) continue;

    const targetLine = lines[gap.lineIndexAfter];

    // Skip blank lines
    if (targetLine.isBlank) continue;

    // Check if we already have a trigger for this line (from first line check)
    if (triggers.some((t) => t.lineIndex === gap.lineIndexAfter)) continue;

    const countInStart = targetLine.timestamp - beatInterval * minBeats;
    const countInEnd = targetLine.timestamp;

    triggers.push({
      lineIndex: gap.lineIndexAfter,
      gapDuration: gap.duration,
      countInStart,
      countInEnd,
      beatInterval,
    });
  }

  return triggers;
}

/**
 * Main function: Parse LRC and calculate all count-in data
 */
export function parseLrcWithCountIn(
  lrcContent: string,
  bpm: number | undefined,
): ParsedLrcData | null {
  if (!lrcContent) return null;

  // Parse LRC lines
  const lines = parseLrc(lrcContent);
  if (lines.length === 0) return null;

  // Find instrumental gaps
  const gaps = findInstrumentalGaps(lines);

  // Calculate count-in triggers
  const countInTriggers = calculateCountInTriggers(lines, gaps, bpm);

  return {
    lines,
    gaps,
    countInTriggers,
  };
}

/**
 * Attach word-level timestamps from a forced alignment result to parsed LRC lines.
 *
 * Each word is assigned to the LRC line with the highest timestamp ≤ word.start.
 * This is more reliable than matching by line_index because the backend and
 * frontend use different raw-file index schemes.
 *
 * Returns a new lines array — original array is not mutated.
 */
export function attachWordTimestamps(
  lines: LrcLine[],
  words: WordTimestamp[],
): LrcLine[] {
  if (!words || words.length === 0) return lines;

  const EARLY_LINE_START_TOLERANCE_SEC = 0.8;

  const lineIndexToParsedIndex = new Map<number, number>();
  lines.forEach((line, parsedIndex) => {
    lineIndexToParsedIndex.set(line.sourceLineIndex, parsedIndex);
  });

  // lines are sorted by timestamp (guaranteed by parseLrc)
  const lineTimestampsSec = lines.map((l) => l.timestamp / 1000);

  const getTimestampLineIdx = (wordStartSec: number): number => {
    let matchedIdx = -1;
    for (let i = 0; i < lineTimestampsSec.length; i++) {
      if (lineTimestampsSec[i] <= wordStartSec) {
        matchedIdx = i;
      } else {
        break;
      }
    }
    return matchedIdx;
  };

  // Prefer the backend's explicit line_index when it stays consistent with the
  // word timing. WhisperX can split one lyric line into multiple output
  // segments, which shifts subsequent segment indexes even though the word
  // timestamps still line up with the original LRC line.
  const pickLineIdxForGroup = (
    groupStartSec: number,
    mappedLineIdx: number,
  ): number => {
    const timestampLineIdx = getTimestampLineIdx(groupStartSec);

    if (mappedLineIdx === -1) {
      return timestampLineIdx;
    }

    if (timestampLineIdx === -1) {
      const mappedLineStartSec = lineTimestampsSec[mappedLineIdx];
      return groupStartSec >= mappedLineStartSec - EARLY_LINE_START_TOLERANCE_SEC
        ? mappedLineIdx
        : -1;
    }

    if (mappedLineIdx === timestampLineIdx) {
      return mappedLineIdx;
    }

    if (mappedLineIdx === timestampLineIdx + 1) {
      const mappedLineStartSec = lineTimestampsSec[mappedLineIdx];
      return groupStartSec >= mappedLineStartSec - EARLY_LINE_START_TOLERANCE_SEC
        ? mappedLineIdx
        : timestampLineIdx;
    }

    return timestampLineIdx;
  };

  const byLineIdx = new Map<number, WordTimestamp[]>();
  for (let i = 0; i < words.length; ) {
    const groupLineIndex = words[i].line_index;
    const group: WordTimestamp[] = [];

    while (i < words.length && words[i].line_index === groupLineIndex) {
      group.push(words[i]);
      i += 1;
    }

    const mappedLineIdx = lineIndexToParsedIndex.get(groupLineIndex) ?? -1;
    if (mappedLineIdx === -1) {
      for (const word of group) {
        const lineIdx = getTimestampLineIdx(word.start);
        if (lineIdx === -1) continue;
        const bucket = byLineIdx.get(lineIdx) ?? [];
        bucket.push(word);
        byLineIdx.set(lineIdx, bucket);
      }
      continue;
    }

    const lineIdx = pickLineIdxForGroup(group[0].start, mappedLineIdx);
    if (lineIdx === -1) continue;

    const bucket = byLineIdx.get(lineIdx) ?? [];
    bucket.push(...group);
    byLineIdx.set(lineIdx, bucket);
  }

  return lines.map((line, idx) => {
    const lineWords = byLineIdx.get(idx);
    if (!lineWords || lineWords.length === 0) return line;
    return { ...line, words: lineWords };
  });
}
