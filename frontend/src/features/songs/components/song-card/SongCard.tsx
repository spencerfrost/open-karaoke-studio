import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { useSongActions } from "../../hooks/useSongActions";
import { useSongDialogs } from "../../hooks/useSongDialogs";
import { SongArtwork } from "./SongArtwork";
import { SongInfo } from "./SongInfo";
import { SongActions } from "./SongActions";
import { SongDetailsDialog } from "../song-details/SongDetailsDialog";
import { JoinSessionDialog } from "../JoinSessionDialog";
import { DeleteSongDialog } from "../DeleteSongDialog";
import { SongCardProps } from "./SongCard.types";

export const SongCard: React.FC<SongCardProps> = ({
  song,
  variant = "detailed",
  actions = ["queue", "details"],
  sessionId,
}) => {
  const { getArtworkUrl } = useSongs();
  const { isHost } = useSessionStore();
  const artworkUrl = getArtworkUrl(song, "medium");

  const songActions = useSongActions(song, {  }, sessionId);
  const dialogs = useSongDialogs();
  const [showJoinDialog, setShowJoinDialog] = useState(false);

  const handleQueueClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (songActions.handleQueueClick()) {
      // Song was added directly (user is in session)
      // Could show a success toast here
    } else {
      // User not in session, show join dialog
      setShowJoinDialog(true);
    }
  };

  const handleJoinSuccess = (singerName: string) => {
    // After successful join, add the song to queue
    songActions.handleAddToQueue(singerName);
    setShowJoinDialog(false);
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
            showPlayButton={isHost}
          />
          <SongInfo song={song} />
        </div>
      </CardContent>

      <SongActions
        song={song}
        onQueue={showAction("queue") ? handleQueueClick : undefined}
        onDelete={showAction("delete") ? handleDeleteClick : undefined}
        onDetails={showAction("details") ? handleDetailsClick : undefined}
      />

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
    </Card>
  );
};

export default SongCard;
