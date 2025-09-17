import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useSongs } from "@/hooks/api/useSongs";
import { useSongActions } from "@/hooks/useSongActions";
import { useSongDialogs } from "@/hooks/useSongDialogs";
import { SongArtwork } from "./SongArtwork";
import { SongInfo } from "./SongInfo";
import { SongActions } from "./SongActions";
import { SongDetailsDialog } from "../song-details/SongDetailsDialog";
import { SingerNameDialog } from "../SingerNameDialog";
import { DeleteSongDialog } from "../DeleteSongDialog";
import { SongCardProps } from "./SongCard.types";

export const SongCard: React.FC<SongCardProps> = ({
  song,
  onPlay,
  variant = "detailed",
  actions = ["queue", "details"],
  sessionId,
}) => {
  const { getArtworkUrl } = useSongs();
  const artworkUrl = getArtworkUrl(song, "medium");

  const songActions = useSongActions(song, { onPlay }, sessionId);
  const dialogs = useSongDialogs();

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dialogs.openDialog("singer");
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dialogs.openDialog("delete");
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dialogs.openDialog("details");
  };

  const showAction = (action: string) =>
    actions.includes(action as "delete" | "details" | "queue");

  return (
    <Card className="group overflow-hidden relative hover:shadow-lg transition-shadow pt-0 pb-2 gap-0.5">
      <CardContent className="p-0 flex-1">
        <div className="flex flex-col">
          <SongArtwork
            song={song}
            artworkUrl={artworkUrl}
            showSyncedBadge={variant === "detailed"}
            onPlay={songActions.handlePlay}
          />
          <SongInfo song={song} />
        </div>
      </CardContent>

      <SongActions
        onQueue={showAction("queue") ? handleQueueClick : undefined}
        onDelete={showAction("delete") ? handleDeleteClick : undefined}
        onDetails={showAction("details") ? handleDetailsClick : undefined}
      />

      <SongDetailsDialog
        song={song}
        isOpen={dialogs.isDialogOpen("details")}
        onClose={dialogs.closeDialog}
      />

      <SingerNameDialog
        isOpen={dialogs.isDialogOpen("singer")}
        onClose={dialogs.closeDialog}
        onConfirm={songActions.handleAddToQueue}
        songTitle={song.title}
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
    </Card>
  );
};

export default SongCard;
