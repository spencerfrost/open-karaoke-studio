import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useSongs } from "@/hooks/api/useSongs";
import { useSongActions } from "@/hooks/useSongActions";
import { useSongDialogs } from "@/hooks/useSongDialogs";
import { SongArtwork } from "./SongArtwork";
import { SongInfo } from "./SongInfo";
import { SongActions } from "./SongActions";
import { SongDialogs } from "./SongDialogs";
import { SongCardProps } from "./SongCard.types";

export const SongCard: React.FC<SongCardProps> = ({
  song,
  onPlay,
  variant = "detailed",
  actions = ["queue", "details"],
}) => {
  const { getArtworkUrl } = useSongs();
  const artworkUrl = getArtworkUrl(song, "medium");

  const songActions = useSongActions(song, { onPlay });
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
    <Card className="group overflow-hidden relative hover:shadow-lg transition-shadow pt-0">
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
      <SongDialogs song={song} dialogs={dialogs} songActions={songActions} />
    </Card>
  );
};

export default SongCard;
