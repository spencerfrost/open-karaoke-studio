import type { LrcLine, WordTimestamp } from "@/utils/lrcParser";

/**
 * Aligned word timings are authoritative whenever they exist — that is the
 * whole point of running forced alignment. The LRC timestamp is only a rough
 * tag and is used solely as the fallback for lines alignment did not cover.
 *
 * Blending the two (taking the earlier/later of the pair) breaks instrumental
 * breaks: alignment discovers the vocal starts *later* than the stale LRC tag,
 * so a blend would light the line up mid-break, while the instrumental progress
 * bar — which trusts the aligned times — is still filling.
 */
function getLineStartMs(line: LrcLine): number {
  if (!line.words || line.words.length === 0) return line.timestamp;

  return line.words.reduce(
    (earliest, word) => Math.min(earliest, word.start * 1000),
    Number.POSITIVE_INFINITY,
  );
}

function getLineEndMs(
  lines: LrcLine[],
  contentLineIndices: number[],
  contentPosition: number,
): number {
  const currentLine = lines[contentLineIndices[contentPosition]];
  const nextContentLineIndex = contentLineIndices[contentPosition + 1];
  const nextContentLine =
    nextContentLineIndex !== undefined ? lines[nextContentLineIndex] : null;
  const nextContentStartMs = nextContentLine
    ? getLineStartMs(nextContentLine)
    : Number.POSITIVE_INFINITY;

  if (!currentLine.words || currentLine.words.length === 0) {
    return nextContentStartMs;
  }

  const lastWordEndMs = currentLine.words.reduce(
    (latest, word) => Math.max(latest, word.end * 1000),
    Number.NEGATIVE_INFINITY,
  );
  return Math.min(lastWordEndMs, nextContentStartMs);
}

export function lineHasWordTiming(line: LrcLine): boolean {
  return !!line.words && line.words.length > 0;
}

/** Below this score the aligner did not really find the word in the audio. */
const UNHEARD_SCORE = 0.1;
/** A start this soon after the previous word's is a packed placeholder (s). */
const PACKED_STEP_SEC = 0.1;

function isUnheard(word: WordTimestamp, threshold: number): boolean {
  return word.score !== undefined && word.score < threshold;
}

/**
 * When forced alignment can't hear a line's words it still places them: one
 * word (usually the first) stretches over most of the line and the rest are
 * packed one frame apart at its end, with scores near zero. Highlighted word
 * by word, the line freezes on that word and then flashes through the rest.
 *
 * Fast singing is not the signal — rap really does hit 10 words a second, and
 * those words score well. Packed *and* unheard is.
 */
export function isWordTimingCrammed(words: WordTimestamp[]): boolean {
  if (words.length < 3) return false;

  const packedUnheard = words
    .slice(1)
    .filter(
      (word, i) =>
        isUnheard(word, UNHEARD_SCORE) &&
        word.start - words[i].start < PACKED_STEP_SEC,
    ).length;
  if (packedUnheard >= Math.max(2, 0.4 * (words.length - 1))) return true;

  const span = words[words.length - 1].end - words[0].start;
  if (span <= 1) return false;

  const holdIndex = words
    .slice(0, -1)
    .findIndex((word) => (word.end - word.start) / span > 0.5);
  if (holdIndex === -1) return false;

  const after = words.slice(holdIndex + 1);
  const unheardAfter = after.filter((word) =>
    isUnheard(word, UNHEARD_SCORE * 2),
  ).length;
  return unheardAfter >= Math.max(1, after.length / 2);
}

/**
 * How a line shows its progress: word by word when alignment timed it,
 * a sweep across the line when alignment crammed it, or not at all.
 */
export type LineRenderMode = "words" | "sweep" | "content";

export function getLineRenderMode(line: LrcLine): LineRenderMode {
  if (!line.words || line.words.length === 0) return "content";
  return isWordTimingCrammed(line.words) ? "sweep" : "words";
}

/** How far the sweep has crossed a line, from its first word to its last. */
export function getSweepProgress(
  words: WordTimestamp[],
  currentTimeSec: number,
): number {
  const start = words[0].start;
  const end = words[words.length - 1].end;
  if (end <= start) return currentTimeSec >= start ? 1 : 0;
  return Math.max(0, Math.min(1, (currentTimeSec - start) / (end - start)));
}

export function anyLineHasWordTiming(lines: LrcLine[]): boolean {
  return lines.some((line) => !line.isBlank && lineHasWordTiming(line));
}

export function getActiveLineIndex(
  lines: LrcLine[],
  currentTimeMs: number,
): number {
  if (lines.length === 0) return -1;

  const contentLineIndices = lines.reduce<number[]>((indices, line, index) => {
    if (!line.isBlank) {
      indices.push(index);
    }
    return indices;
  }, []);

  if (contentLineIndices.length === 0) return -1;

  const hasWordTimings = anyLineHasWordTiming(lines);

  if (!hasWordTimings) {
    const fallbackIndex = lines.findIndex((line, index) => {
      const nextLine = lines[index + 1];
      return (
        currentTimeMs >= line.timestamp &&
        (!nextLine || currentTimeMs < nextLine.timestamp)
      );
    });

    if (fallbackIndex !== -1) {
      return fallbackIndex;
    }

    return currentTimeMs < lines[0].timestamp ? -1 : lines.length - 1;
  }

  let activeIndex = -1;

  for (let position = 0; position < contentLineIndices.length; position++) {
    const lineIndex = contentLineIndices[position];
    const startMs = getLineStartMs(lines[lineIndex]);
    const endMs = getLineEndMs(lines, contentLineIndices, position);

    if (currentTimeMs >= startMs && currentTimeMs < endMs) {
      activeIndex = lineIndex;
    }
  }

  return activeIndex;
}
