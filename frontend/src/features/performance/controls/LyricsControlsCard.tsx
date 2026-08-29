/**
 * LyricsControlsCard - search, timing offset and size, in priority order.
 *
 * Named to avoid colliding with the library's LyricsCard. The search and paste
 * dialogs (and their update mutations) come from the old settings-menu
 * LyricsEditView — lyrics search now exists on the phone as well as the stage.
 */

import React, { useCallback, useMemo, useState } from "react";
import { Captions, FileText, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import type { LyricsResult } from "@/features/lyrics/components/LyricsFetchDialog";
import type { Song } from "@/types/Song";
import { cn } from "@/lib/utils";
import LyricsOffsetRow from "./LyricsOffsetRow";
import LyricsSizeRow from "./LyricsSizeRow";
import {
  cardClass,
  cardIconSize,
  cardLabelClass,
  type Density,
} from "./density";

interface LyricsControlsCardProps {
  density: Density;
  className?: string;
}

const LyricsControlsCard: React.FC<LyricsControlsCardProps> = ({
  density,
  className,
}) => {
  const isTv = density === "tv";

  const songId = useKaraokePlayerStore((state) => state.songId);
  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  const updateSongMutation = useUpdateSong();

  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] = useState(false);

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
    [songId, song],
  );

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
    <div className={cardClass(density, cn("shrink-0", className))}>
      <div className="flex items-center gap-2.5">
        <Captions size={cardIconSize(density)} className="text-primary" />
        <span className={cardLabelClass(density)}>Lyrics</span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          disabled={!song}
          onClick={() => setIsLyricsDialogOpen(true)}
          className={cn(
            "flex-1 font-semibold",
            isTv ? "h-17 text-xl" : "h-13 text-base",
          )}
        >
          <Search className={cn("mr-1", isTv ? "size-6" : "size-4.5")} />
          Search &amp; Replace
        </Button>
        <Button
          variant="outline"
          disabled={!song}
          onClick={() => setIsPasteLyricsDialogOpen(true)}
          aria-label="Paste lyrics"
          title="Paste lyrics"
          className={cn("shrink-0", isTv ? "h-17 w-16" : "h-13 w-12")}
        >
          <FileText className={isTv ? "size-6" : "size-4.5"} />
        </Button>
      </div>

      <LyricsOffsetRow density={density} />
      <LyricsSizeRow density={density} />

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

export default LyricsControlsCard;
