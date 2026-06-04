/**
 * LyricsDisplay - Pure component for rendering synced/unsynced lyrics
 * Handles scrolling, highlighting, and different sizes
 * Optimized for performance with smooth scrolling and proper accessibility
 */

import React, { memo, useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Search, FileText, Mic2, Loader2 } from "lucide-react";
import LyricsFetchDialog from "./LyricsFetchDialog";
import PasteLyricsDialog from "./PasteLyricsDialog";
import { useSongs } from "@/hooks/api/useSongs";
import { useApiMutation } from "@/hooks/api/useApi";
import { toast } from "sonner";
import type { LyricsResult } from "./LyricsFetchDialog";
import type { Song } from "@/types/Song";
import KaraokeLyricsRenderer from "./KaraokeLyricsRenderer";
import { parseLrcWithCountIn, attachWordTimestamps } from "@/utils/lrcParser";
import { useLyricsAlignment } from "@/hooks/api/useLyricsAlignment";
import { useQueryClient } from "@tanstack/react-query";

interface CountInStyleConfig {
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;
}

interface LyricsDisplayProps {
  lyrics: string;
  isSync: boolean;
  currentTime: number; // in seconds
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number; // in milliseconds
  className?: string;
  "aria-label"?: string;
  // Optional song data for lyrics search
  songId?: string;
  songTitle?: string;
  songArtist?: string;
  songAlbum?: string;
  songDuration?: number; // in seconds
  // Optional seek callback for clicking on lyrics
  onSeek?: (timeSeconds: number) => void;
  // Optional BPM for count-in (only used for synced lyrics)
  bpm?: number;
  // Optional count-in style configuration
  countInStyle?: CountInStyleConfig;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = memo(
  ({
    lyrics,
    isSync,
    currentTime,
    lyricsSize,
    lyricsOffset,
    className = "",
    "aria-label": ariaLabel = "Song lyrics",
    songId,
    songTitle,
    songArtist,
    songAlbum,
    songDuration,
    onSeek,
    bpm,
    countInStyle,
  }) => {
    const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
    const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] =
      useState(false);
    const queryClient = useQueryClient();
    const { useUpdateSong } = useSongs();
    const updateSongMutation = useUpdateSong();

    const transcribeLyricsMutation = useApiMutation<{ job_id?: string; status?: string }, void>(
      "lyrics/songs/transcribe-placeholder/align",
      "post",
      {
        mutationFn: async () => {
          if (!songId) {
            throw new Error("Missing song ID");
          }

          const response = await fetch(`/api/lyrics/songs/${songId}/align`, {
            method: "POST",
            credentials: "include",
          });

          if (!response.ok) {
            let errorMessage = `Failed to start transcription (${response.status})`;
            try {
              const contentType = response.headers.get("Content-Type") || "";
              if (contentType.includes("application/json")) {
                const errorData = await response.json();
                errorMessage =
                  errorData?.detail || errorData?.error || errorData?.message || errorMessage;
              }
            } catch {
              // Keep fallback error message when response parsing fails.
            }
            throw new Error(errorMessage);
          }

          return response.json();
        },
        onSuccess: () => {
          toast.success("Transcription started. Lyrics will appear when processing completes.");
          if (songId) {
            queryClient.invalidateQueries({ queryKey: ["songs", songId] });
            queryClient.invalidateQueries({ queryKey: ["lyrics", songId, "alignment"] });
          }
        },
        onError: (error) => {
          toast.error(`Failed to start transcription: ${error.message}`);
        },
      },
    );

    const handleTranscribeLyrics = () => {
      if (!songId) {
        toast.error("Missing song information");
        return;
      }
      transcribeLyricsMutation.mutate();
    };

    const handleLyricsSearch = () => {
      if (!songId || !songTitle || !songArtist) {
        toast.error("Missing song information for lyrics search");
        return;
      }
      setIsLyricsDialogOpen(true);
    };

    const handleLyricsSelected = (lyricsResult: LyricsResult) => {
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
    };

    const handlePasteLyrics = () => {
      if (!songId) {
        toast.error("Missing song information");
        return;
      }
      setIsPasteLyricsDialogOpen(true);
    };

    const handlePasteLyricsConfirmed = (pastedLyrics: string) => {
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
    };

    const lyricsSizeClass =
      lyricsSize === "small"
        ? "text-base"
        : lyricsSize === "large"
          ? "text-3xl"
          : "text-xl";

    // Stable song object for LyricsFetchDialog — prevents re-triggering the
    // dialog's search useEffect on every currentTime re-render (every 100ms)
    const songForDialog = useMemo(
      () =>
        songId && songTitle && songArtist
          ? ({
              id: songId,
              title: songTitle,
              artist: songArtist,
              album: songAlbum || "",
              duration: songDuration,
            } as Song)
          : null,
      [songId, songTitle, songArtist, songAlbum, songDuration],
    );

    // Parse lyrics data for synced display
    const parsedLrcData = useMemo(() => {
      if (!isSync || !lyrics) return null;
      return parseLrcWithCountIn(lyrics, bpm);
    }, [isSync, lyrics, bpm]);

    const { words: alignmentWords, instrumentalIntervals } = useLyricsAlignment(
      isSync ? songId : undefined,
    );

    const parsedLrcDataWithWords = useMemo(() => {
      if (!parsedLrcData) return null;
      if (!alignmentWords || alignmentWords.length === 0) {
        return {
          ...parsedLrcData,
          ...(instrumentalIntervals
            ? { instrumentalIntervals }
            : {}),
        };
      }
      return {
        ...parsedLrcData,
        lines: attachWordTimestamps(parsedLrcData.lines, alignmentWords),
        ...(instrumentalIntervals
          ? { instrumentalIntervals }
          : {}),
      };
    }, [parsedLrcData, alignmentWords, instrumentalIntervals]);

    if (isSync) {
      if (!lyrics || !parsedLrcDataWithWords) {
        return (
          <div
            className={`flex items-center justify-center h-full w-full ${className}`}
            role="region"
            aria-label={ariaLabel}
          >
            <div className="flex flex-col items-center gap-4">
              <div className="text-background/50 text-lg">
                No synced lyrics available
              </div>
              {songId && (
                <Button
                  onClick={handleTranscribeLyrics}
                  variant="outline"
                  size="sm"
                  disabled={transcribeLyricsMutation.isPending}
                >
                  {transcribeLyricsMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Mic2 className="w-4 h-4 mr-2" />
                  )}
                  Transcribe Lyrics
                </Button>
              )}
            </div>
          </div>
        );
      }

      return (
        <div className={`relative h-full w-full ${className}`}>
          <KaraokeLyricsRenderer
            parsedData={parsedLrcDataWithWords}
            currentTime={currentTime}
            lyricsSize={lyricsSize}
            lyricsOffset={lyricsOffset}
            bpm={bpm}
            countInStyle={countInStyle}
            onSeek={onSeek}
          />

          {/* Bottom vignette fade */}
          <div className="absolute bottom-0 left-0 right-0 h-64 bg-gradient-to-b from-transparent to-black/100 pointer-events-none" />
        </div>
      );
    }

    return (
      <div
        className={`w-full h-full overflow-y-auto scrollbar-hide ${className}`}
        role="region"
        aria-label={ariaLabel}
      >
        {lyrics ? (
          <div
            className={`text-2xl font-semibold text-background whitespace-pre-line text-center ${lyricsSizeClass}`}
            role="document"
          >
            {lyrics}
          </div>
        ) : (
          <div
            className="flex flex-col items-center justify-center h-full text-center p-8"
            role="status"
          >
            <div className="text-gray-400 text-lg mb-2">
              🎵 No lyrics available
            </div>
            <div className="text-gray-500 text-sm mb-4">
              Enjoy the music and sing along if you know the words!
            </div>
            {(songForDialog || songId) && (
              <div className="flex gap-2">
                {songForDialog && (
                  <Button
                    onClick={handleLyricsSearch}
                    variant="outline"
                    size="sm"
                    className="mt-2"
                  >
                    <Search className="w-4 h-4 mr-2" />
                    Search for Lyrics
                  </Button>
                )}
                {songForDialog && (
                  <Button
                    onClick={handlePasteLyrics}
                    variant="outline"
                    size="sm"
                    className="mt-2"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Paste Lyrics
                  </Button>
                )}
                {songId && (
                  <Button
                    onClick={handleTranscribeLyrics}
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    disabled={transcribeLyricsMutation.isPending}
                  >
                    {transcribeLyricsMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Mic2 className="w-4 h-4 mr-2" />
                    )}
                    Transcribe Lyrics
                  </Button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Lyrics Search Dialog */}
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
  },
);

LyricsDisplay.displayName = "LyricsDisplay";

export default LyricsDisplay;
