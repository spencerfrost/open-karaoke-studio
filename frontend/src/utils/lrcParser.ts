/**
 * LRC Parser
 * Parses LRC lyrics into timed lines and attaches word-level forced-alignment data.
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

export interface InstrumentalInterval {
  start: number; // seconds
  end: number; // seconds
  duration: number; // seconds
  lead_in_start: number; // seconds
  next_line_index: number;
  confidence: number;
  source: string;
}

export interface ParsedLrcData {
  lines: LrcLine[];
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
 * Main function: parse LRC content into the structure the renderer consumes.
 */
export function parseLrcData(lrcContent: string): ParsedLrcData | null {
  if (!lrcContent) return null;

  const lines = parseLrc(lrcContent);
  if (lines.length === 0) return null;

  return { lines };
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

  // Blank LRC lines are spacers — they render as empty vertical gaps and can
  // never own sung words. Attaching words to one silently misplaces everything
  // anchored to that line (instrumental progress bars, the active highlight),
  // so blanks are excluded from every candidate lookup below.
  const lineIndexToParsedIndex = new Map<number, number>();
  lines.forEach((line, parsedIndex) => {
    if (line.isBlank) return;
    lineIndexToParsedIndex.set(line.sourceLineIndex, parsedIndex);
  });

  // lines are sorted by timestamp (guaranteed by parseLrc)
  const lineTimestampsSec = lines.map((l) => l.timestamp / 1000);

  const getTimestampLineIdx = (wordStartSec: number): number => {
    let matchedIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lineTimestampsSec[i] > wordStartSec) break;
      if (lines[i].isBlank) continue;
      matchedIdx = i;
    }
    return matchedIdx;
  };

  // The next content line after `fromIdx`, skipping blank spacers. Used so the
  // "off by one line" tolerance below still recognises adjacency when a blank
  // line sits between the two candidates.
  const nextContentLineIdx = (fromIdx: number): number => {
    for (let i = fromIdx + 1; i < lines.length; i++) {
      if (!lines[i].isBlank) return i;
    }
    return -1;
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
      return groupStartSec >=
        mappedLineStartSec - EARLY_LINE_START_TOLERANCE_SEC
        ? mappedLineIdx
        : -1;
    }

    if (mappedLineIdx === timestampLineIdx) {
      return mappedLineIdx;
    }

    if (mappedLineIdx === nextContentLineIdx(timestampLineIdx)) {
      const mappedLineStartSec = lineTimestampsSec[mappedLineIdx];
      return groupStartSec >=
        mappedLineStartSec - EARLY_LINE_START_TOLERANCE_SEC
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
