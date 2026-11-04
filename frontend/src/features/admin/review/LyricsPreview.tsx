import React from "react";
import { parseLrc } from "@/utils/lrcParser";
import { formatTime } from "@/utils/formatters";

/** The lyrics as they are now: timed lines when there are some. */
export const LyricsPreview: React.FC<{
  syncedLyrics?: string;
  plainLyrics?: string;
}> = ({ syncedLyrics, plainLyrics }) => {
  const timed = syncedLyrics
    ? parseLrc(syncedLyrics).filter((line) => !line.isBlank)
    : [];

  if (!timed.length && !plainLyrics) {
    return <p className="text-sm text-muted-foreground">No lyrics.</p>;
  }

  return (
    <div className="max-h-80 overflow-y-auto rounded-md border border-border/60 bg-muted/30 p-3 text-sm leading-relaxed">
      {timed.length ? (
        <ol className="space-y-0.5">
          {timed.map((line, index) => (
            <li key={index} className="flex gap-3">
              <span className="w-10 shrink-0 text-right font-mono text-xs leading-relaxed text-muted-foreground">
                {formatTime(line.timestamp / 1000)}
              </span>
              <span>{line.content}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="whitespace-pre-line">{plainLyrics}</p>
      )}
    </div>
  );
};
