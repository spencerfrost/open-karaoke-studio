import React, { useMemo } from "react";
import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface LyricsPreviewProps {
  plainLyrics?: string;
  syncedLyrics?: string;
  className?: string;
}

/** Strip LRC timestamps like [00:12.34] from synced lyrics */
function stripLrcTimestamps(syncedLyrics: string): string {
  return syncedLyrics
    .replace(/\[\d{2}:\d{2}\.\d{2,3}]/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");
}

export const LyricsPreview: React.FC<LyricsPreviewProps> = ({
  plainLyrics,
  syncedLyrics,
  className,
}) => {
  const displayText = useMemo(() => {
    if (plainLyrics) return plainLyrics;
    if (syncedLyrics) return stripLrcTimestamps(syncedLyrics);
    return null;
  }, [plainLyrics, syncedLyrics]);

  if (!displayText) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 py-4 text-sm text-muted-foreground",
          className,
        )}
      >
        <FileText size={16} />
        <span>No lyrics available</span>
      </div>
    );
  }

  return (
    <div className={cn("max-h-48 overflow-y-auto rounded-md", className)}>
      <pre className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap font-sans">
        {displayText}
      </pre>
    </div>
  );
};
