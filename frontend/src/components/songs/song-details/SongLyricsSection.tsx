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
  const hasLyrics = !!(song.lyrics || song.syncedLyrics);
  const hasSyncedLyrics = !!song.syncedLyrics;

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

  const displayLyrics = song.lyrics || "";
  
  // Basic processing for display
  const processedLyrics = displayLyrics
    .split('\n')
    .filter(line => line.trim().length > 0)
    .map(line => line.trim());

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
      
      {hasSyncedLyrics && (
        <div className="mt-4 p-3 bg-muted/30 rounded border text-xs text-muted-foreground">
          <Music size={12} className="inline mr-1" />
          This song includes synchronized lyrics for karaoke playback
        </div>
      )}
    </div>
  );
};
