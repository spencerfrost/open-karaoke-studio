/**
 * LyricsEditView - Detailed lyrics controls with timing offset drag
 * Includes auto-scroll toggle, text size, timing offset with drag, and lyrics search/paste
 */

import React, { useState, useCallback, useMemo } from "react";
import { ChevronLeft, Search, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import type { LyricsResult } from "@/features/lyrics/components/LyricsFetchDialog";
import type { Song } from "@/types/Song";

interface LyricsEditViewProps {
  onBack: () => void;
}

const LyricsEditView: React.FC<LyricsEditViewProps> = ({ onBack }) => {
  const songId = useKaraokePlayerStore((state) => state.songId);

  // Fetch current song for synced lyrics
  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  const updateSongMutation = useUpdateSong();

  const songForDialog = useMemo<Song | null>(
    () =>
      song
        ? ({
            id: songId,
            title: song.title,
            artist: song.artist,
            album: song.album || "",
            duration: song.duration,
          } as Song)
        : null,
    [songId, song?.title, song?.artist, song?.album, song?.duration],
  );

  // Lyrics dialog state
  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] = useState(false);

  // Lyrics search/paste handlers
  const handleLyricsSelected = useCallback(
    (lyricsResult: LyricsResult) => {
      if (!songId) {
        toast.error("Cannot update song: missing song ID");
        return;
      }

      updateSongMutation.mutate(
        {
          id: songId,
          plainLyrics: lyricsResult.plainLyrics,
          syncedLyrics: lyricsResult.syncedLyrics,
        },
        {
          onSuccess: () => {
            setIsLyricsDialogOpen(false);
          },
          onError: (error) => {
            toast.error(`Failed to update lyrics: ${error.message}`);
          },
        },
      );
    },
    [songId, updateSongMutation],
  );

  const handlePasteLyricsConfirmed = useCallback(
    (pastedLyrics: string) => {
      if (!songId) {
        toast.error("Cannot update song: missing song ID");
        return;
      }

      updateSongMutation.mutate(
        {
          id: songId,
          plainLyrics: pastedLyrics,
          syncedLyrics: undefined, // Clear synced lyrics when pasting plain lyrics
        },
        {
          onSuccess: () => {
            setIsPasteLyricsDialogOpen(false);
          },
          onError: (error) => {
            toast.error(`Failed to save lyrics: ${error.message}`);
          },
        },
      );
    },
    [songId, updateSongMutation],
  );

  return (
    <div className="py-2">
      {/* Header with back button */}
      <div className="px-4 py-3 border-b border-white/10">
        <button
          onClick={onBack}
          className="flex items-center gap-2 hover:text-orange-peel transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Lyrics</h2>
        </button>
      </div>

      {/* Content */}
      <div className="px-4 py-4 space-y-4">
        {/* Lyrics Search/Replace Buttons */}
        {song && (
          <>
            <Separator className="bg-white/10" />
            <div className="space-y-2">
              <Label className="text-background">Find or Replace Lyrics</Label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLyricsDialogOpen(true)}
                  className="flex-1 text-background border-white/20 hover:bg-white/10"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Search
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsPasteLyricsDialogOpen(true)}
                  className="flex-1 text-background border-white/20 hover:bg-white/10"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Paste
                </Button>
              </div>
              <p className="text-xs text-background/40">
                Search for better lyrics or paste your own
              </p>
            </div>
          </>
        )}
      </div>

      {/* Lyrics Dialogs */}
      {songForDialog && (
        <>
          <LyricsFetchDialog
            isOpen={isLyricsDialogOpen}
            onClose={() => setIsLyricsDialogOpen(false)}
            song={songForDialog}
            onLyricsSelected={handleLyricsSelected}
          />
          <PasteLyricsDialog
            isOpen={isPasteLyricsDialogOpen}
            onClose={() => setIsPasteLyricsDialogOpen(false)}
            onLyricsConfirmed={handlePasteLyricsConfirmed}
          />
        </>
      )}
    </div>
  );
};

export default LyricsEditView;
