import React, { useState } from "react";
import { Music, ListPlus, MoreVertical, Trash, Loader2 } from "lucide-react";
import { Song } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { useSongActions } from "@/features/songs/hooks/useSongActions";
import { useSongDialogs } from "@/features/songs/hooks/useSongDialogs";
import { SongDetailsDialog } from "@/features/songs/components/song-details/SongDetailsDialog";
import { JoinSessionDialog } from "@/features/songs/components/JoinSessionDialog";
import { DeleteSongDialog } from "@/features/songs/components/DeleteSongDialog";

function formatDuration(seconds?: number): string {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface SongTableRowProps {
  song: Song;
}

const SongTableRow: React.FC<SongTableRowProps> = ({ song }) => {
  const { getArtworkUrl } = useSongs();
  const { isHost } = useSessionStore();
  const isProcessing = useProcessingIndicators((state) =>
    state.isProcessing(song.id),
  );
  const [imgError, setImgError] = useState(false);
  const [showJoinDialog, setShowJoinDialog] = useState(false);

  const songActions = useSongActions(song);
  const dialogs = useSongDialogs();

  const artworkUrl = getArtworkUrl(song, "small");

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (songActions.handleQueueClick()) {
      // added directly
    } else {
      setShowJoinDialog(true);
    }
  };

  const handleJoinSuccess = (singerName: string) => {
    songActions.handleAddToQueue(singerName);
    setShowJoinDialog(false);
  };

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-lemon-chiffon/5 group">
      {/* Thumbnail */}
      <div className="w-9 h-9 rounded flex-shrink-0 overflow-hidden bg-orange-peel/20 flex items-center justify-center">
        {artworkUrl && !imgError ? (
          <img
            src={artworkUrl}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <Music size={14} className="text-orange-peel/60" />
        )}
      </div>

      {/* Title */}
      <span className="flex-1 min-w-0 text-sm text-lemon-chiffon truncate">
        {song.title}
      </span>

      {/* Genre */}
      <span className="hidden sm:block w-28 text-xs text-lemon-chiffon/40 truncate shrink-0">
        {song.primaryGenre ?? ""}
      </span>

      {/* Duration */}
      <span className="w-10 text-xs text-lemon-chiffon/50 text-right shrink-0 tabular-nums">
        {formatDuration(song.duration)}
      </span>

      {/* Actions */}
      <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          className="size-7 text-accent"
          aria-label="Add to karaoke queue"
          onClick={handleQueueClick}
          disabled={isProcessing}
        >
          <ListPlus className="size-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="size-7 text-foreground"
          aria-label="Song details"
          onClick={(e) => {
            e.stopPropagation();
            dialogs.openDialog("details");
          }}
          disabled={isProcessing}
        >
          <MoreVertical className="size-4" />
        </Button>

        {isHost && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-destructive"
            aria-label="Delete song"
            onClick={(e) => {
              e.stopPropagation();
              dialogs.openDialog("delete");
            }}
            disabled={isProcessing}
          >
            <Trash className="size-4" />
          </Button>
        )}
      </div>

      <SongDetailsDialog
        song={song}
        isOpen={dialogs.isDialogOpen("details")}
        onClose={dialogs.closeDialog}
      />

      <JoinSessionDialog
        isOpen={showJoinDialog}
        onClose={() => setShowJoinDialog(false)}
        onJoinSuccess={handleJoinSuccess}
        context={`add "${song.title}" to the karaoke queue`}
      />

      <DeleteSongDialog
        song={song}
        onConfirm={songActions.handleDelete}
        isDeleting={songActions.isDeleting}
        deleteError={songActions.deleteError}
        isOpen={dialogs.isDialogOpen("delete")}
        onOpenChange={(open) => !open && dialogs.closeDialog()}
        trigger={<div style={{ display: "none" }} />}
      />
    </div>
  );
};

interface ArtistSongTableProps {
  songs: Song[];
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
}

const ArtistSongTable: React.FC<ArtistSongTableProps> = React.memo(({
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}) => {
  if (songs.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Column headers */}
      <div className="flex items-center gap-3 px-3 pb-1 border-b border-lemon-chiffon/10">
        <div className="w-9 shrink-0" />
        <span className="flex-1 text-xs text-lemon-chiffon/40 uppercase tracking-wide">
          Title
        </span>
        <span className="hidden sm:block w-28 text-xs text-lemon-chiffon/40 uppercase tracking-wide shrink-0">
          Genre
        </span>
        <span className="w-10 text-xs text-lemon-chiffon/40 uppercase tracking-wide text-right shrink-0">
          Time
        </span>
        <div className="w-[76px] shrink-0" />
      </div>

      {/* Rows */}
      <div>
        {songs.filter(Boolean).map((song) => (
          <SongTableRow key={song.id} song={song} />
        ))}
      </div>

      {/* Load More */}
      {hasNextPage && (
        <div className="flex justify-center mt-4">
          <Button
            onClick={fetchNextPage}
            disabled={isFetchingNextPage}
            variant="outline"
            className="px-8"
          >
            {isFetchingNextPage ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              "Load More Songs"
            )}
          </Button>
        </div>
      )}
    </div>
  );
});

ArtistSongTable.displayName = "ArtistSongTable";

export default ArtistSongTable;
