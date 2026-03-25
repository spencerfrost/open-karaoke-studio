import React from "react";
import { Song } from "@/types/Song";
import { Badge } from "@/components/ui/badge";
import { FileText, Music, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface SongLyricsSectionProps {
  song: Song;
  className?: string;
}

export const SongLyricsSection: React.FC<SongLyricsSectionProps> = ({
  song,
  className = "",
}) => {
  // Check for any type of lyrics - prioritize synced lyrics, then plain lyrics, then unified lyrics field
  const hasSyncedLyrics = !!song.syncedLyrics;
  const hasPlainLyrics = !!song.plainLyrics;
  const hasUnifiedLyrics = !!song.lyrics;
  const hasLyrics = hasSyncedLyrics || hasPlainLyrics || hasUnifiedLyrics;

  if (!hasLyrics) {
    return (
      <div className={cn("border rounded-lg p-6", className)}>
        <div className="flex items-center gap-2 mb-4">
          <FileText size={20} className="text-muted-foreground" />
          <h3 className="text-lg font-semibold">Lyrics</h3>
        </div>

        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertCircle size={16} />
          <span className="text-sm">No lyrics available for this song</span>
        </div>
      </div>
    );
  }

  // Prioritize synced lyrics, then plain lyrics, then unified lyrics field
  const displayLyrics =
    song.syncedLyrics || song.plainLyrics || song.lyrics || "";
  const isUsingSyncedLyrics = !!song.syncedLyrics;

  // Process lyrics for display - handle both synced (LRC) and plain text formats
  const processedLyrics = React.useMemo(() => {
    if (!displayLyrics) return [];

    // If using synced lyrics, they might be in LRC format with timestamps like [00:12.34]
    if (isUsingSyncedLyrics) {
      return displayLyrics
        .split("\n")
        .map((line) => {
          // Remove LRC timestamp format [mm:ss.xx] or [mm:ss.xxx]
          const cleanedLine = line
            .replace(/^\[\d{2}:\d{2}\.\d{2,3}\]\s*/, "")
            .trim();
          return cleanedLine;
        })
        .filter((line) => line.length > 0);
    }

    // For plain lyrics, just split and clean
    return displayLyrics
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => line.trim());
  }, [displayLyrics, isUsingSyncedLyrics]);

  return (
    <div className={cn("border rounded-lg p-6", className)}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText size={20} className="text-muted-foreground" />
          <h3 className="text-lg font-semibold">Lyrics</h3>
        </div>

        <div className="flex gap-2">
          {hasSyncedLyrics && (
            <Badge variant="secondary" className="bg-green-100 text-green-800">
              <Music size={12} className="mr-1" />
              Synced
            </Badge>
          )}
          {hasPlainLyrics && !hasSyncedLyrics && (
            <Badge variant="secondary" className="bg-blue-100 text-blue-800">
              <FileText size={12} className="mr-1" />
              Plain
            </Badge>
          )}
          <Badge variant="outline" className="text-xs">
            {processedLyrics.length} lines
          </Badge>
        </div>
      </div>

      <div className="prose prose-sm max-w-none">
        {processedLyrics.length > 0 ? (
          <div className="space-y-2">
            {processedLyrics.map((line, index) => (
              <p key={index} className="text-sm leading-relaxed">
                {line}
              </p>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <AlertCircle size={16} />
            <span className="text-sm">Lyrics could not be parsed</span>
          </div>
        )}
      </div>

      {hasSyncedLyrics && isUsingSyncedLyrics && (
        <div className="mt-4 p-3 bg-muted/30 rounded border text-xs text-muted-foreground">
          <Music size={12} className="inline mr-1" />
          This song includes synchronized lyrics for karaoke playback
        </div>
      )}

      {hasPlainLyrics && !hasSyncedLyrics && (
        <div className="mt-4 p-3 bg-muted/30 rounded border text-xs text-muted-foreground">
          <FileText size={12} className="inline mr-1" />
          Plain text lyrics (no timing synchronization)
        </div>
      )}
    </div>
  );
};
