import type { LrcLine } from "@/utils/lrcParser";

function getLineStartMs(line: LrcLine): number {
  const firstWordStartMs = line.words?.[0]?.start
    ? line.words[0].start * 1000
    : null;

  return firstWordStartMs === null
    ? line.timestamp
    : Math.min(line.timestamp, firstWordStartMs);
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

  const lastWord = currentLine.words[currentLine.words.length - 1];
  const lastWordEndMs = Math.max(currentLine.timestamp, lastWord.end * 1000);
  return Math.min(lastWordEndMs, nextContentStartMs);
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

  const hasWordTimings = contentLineIndices.some((index) => {
    const words = lines[index].words;
    return !!words && words.length > 0;
  });

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