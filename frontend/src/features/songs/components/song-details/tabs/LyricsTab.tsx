import React, { useState, useCallback } from "react";
import { Song } from "@/types/Song";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Music, AlertCircle, Search } from "lucide-react";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import type { LyricsResult } from "@/features/lyrics/components/LyricsFetchDialog";

interface LyricsTabProps {
  song: Song;
}

export const LyricsTab: React.FC<LyricsTabProps> = ({ song }) => {
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] = useState(false);

  const handleLyricsSelected = useCallback(
    (lyricsResult: LyricsResult) => {
      updateSongMutation.mutate(
        {
          id: song.id,
          plainLyrics: lyricsResult.plainLyrics,
          syncedLyrics: lyricsResult.syncedLyrics,
        },
        {
          onSuccess: () => {
            setIsLyricsDialogOpen(false);
            toast.success("Lyrics updated successfully");
          },
          onError: (error) => {
            toast.error(
              `Failed to update lyrics: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    },
    [song.id, updateSongMutation],
  );

  const handlePasteLyricsConfirmed = useCallback(
    (pastedLyrics: string) => {
      updateSongMutation.mutate(
        {
          id: song.id,
          plainLyrics: pastedLyrics,
          syncedLyrics: undefined,
        },
        {
          onSuccess: () => {
            setIsPasteLyricsDialogOpen(false);
            toast.success("Lyrics pasted successfully");
          },
          onError: (error) => {
            toast.error(
              `Failed to save lyrics: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    },
    [song.id, updateSongMutation],
  );
  // Check for any type of lyrics
  const hasSyncedLyrics = !!song.syncedLyrics;
  const hasPlainLyrics = !!song.plainLyrics;
  const hasLyrics = hasSyncedLyrics || hasPlainLyrics;

  // Prioritize synced lyrics, then plain lyrics
  const displayLyrics = song.syncedLyrics || song.plainLyrics || "";
  const isUsingSyncedLyrics = !!song.syncedLyrics;

  // Process lyrics for display - must be before conditional returns
  const processedLyrics = React.useMemo(() => {
    if (!displayLyrics) return [];

    // If using synced lyrics, they might be in LRC format with timestamps
    if (isUsingSyncedLyrics) {
      return displayLyrics
        .split("\n")
        .map((line: string) => {
          // Remove LRC timestamp format [mm:ss.xx] or [mm:ss.xxx]
          const cleanedLine = line
            .replace(/^\[\d{2}:\d{2}\.\d{2,3}\]\s*/, "")
            .trim();
          return cleanedLine;
        })
        .filter((line: string) => line.length > 0);
    }

    // For plain lyrics, just split and clean
    return displayLyrics
      .split("\n")
      .filter((line: string) => line.trim().length > 0)
      .map((line: string) => line.trim());
  }, [displayLyrics, isUsingSyncedLyrics]);

  return (
    <div className="space-y-4">
      {/* Header with badges */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={20} className="text-muted-foreground" />
          <h3 className="text-lg font-semibold">Song Lyrics</h3>
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
              Plain Text
            </Badge>
          )}
          {hasLyrics && (
            <Badge variant="outline" className="text-xs">
              {processedLyrics.length} lines
            </Badge>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsLyricsDialogOpen(true)}
          disabled={updateSongMutation.isPending}
          className="flex-1 flex items-center justify-center gap-2"
        >
          <Search size={16} />
          Search Lyrics
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsPasteLyricsDialogOpen(true)}
          disabled={updateSongMutation.isPending}
          className="flex-1 flex items-center justify-center gap-2"
        >
          <FileText size={16} />
          Paste Lyrics
        </Button>
      </div>

      {/* No lyrics state */}
      {!hasLyrics && (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle size={48} className="text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Lyrics Available</h3>
          <p className="text-sm text-muted-foreground text-center max-w-md">
            Search for lyrics online or paste them manually above.
          </p>
        </div>
      )}

      {/* Lyrics content */}
      {hasLyrics && <Card>
        <CardContent className="pt-6">
          {processedLyrics.length > 0 ? (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {processedLyrics.map((line: string, index: number) => (
                <p
                  key={index}
                  className="text-base leading-relaxed hover:bg-muted/30 px-2 py-1 rounded transition-colors"
                >
                  {line}
                </p>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
              <AlertCircle size={16} />
              <span className="text-sm">Lyrics could not be parsed</span>
            </div>
          )}
        </CardContent>
      </Card>}

      {/* Info footer */}
      {hasSyncedLyrics && isUsingSyncedLyrics && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          <Music size={14} className="inline mr-2" />
          This song includes synchronized lyrics that will be displayed during
          karaoke playback
        </div>
      )}

      {hasPlainLyrics && !hasSyncedLyrics && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          <FileText size={14} className="inline mr-2" />
          These are plain text lyrics without timing synchronization
        </div>
      )}

      {/* Lyrics Dialogs */}
      <LyricsFetchDialog
        isOpen={isLyricsDialogOpen}
        onClose={() => setIsLyricsDialogOpen(false)}
        song={song}
        onLyricsSelected={handleLyricsSelected}
      />
      <PasteLyricsDialog
        isOpen={isPasteLyricsDialogOpen}
        onClose={() => setIsPasteLyricsDialogOpen(false)}
        onLyricsConfirmed={handlePasteLyricsConfirmed}
      />
    </div>
  );
};
