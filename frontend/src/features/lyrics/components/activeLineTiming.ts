import type { LrcLine } from "@/utils/lrcParser";

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
