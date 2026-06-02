import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { ListPlus, MoreVertical } from "lucide-react";
import { useSongActions } from "../../hooks/useSongActions";
import { useSongDialogs } from "../../hooks/useSongDialogs";
import { SongArtwork } from "./SongArtwork";
import { SongInfo } from "./SongInfo";
import { SongManagementDialog } from "../song-details/SongManagementDialog";
import { JoinSessionDialog } from "../JoinSessionDialog";
import { SongCardProps } from "./SongCard.types";

export const SongCard: React.FC<SongCardProps> = ({
  song,
  variant = "detailed",
  actions = ["queue", "details"],
  sessionId,
  showArtist = true,
}) => {
  const { getArtworkUrl } = useSongs();
  const { isHost } = useSessionStore();
  const artworkUrl = getArtworkUrl(song, "medium");
  const processingStatus = useProcessingIndicators((state) =>
    state.getStatus(song.id),
  );
  const isLyricsOnlyProcessing =
    processingStatus?.engineType === "lyrics_alignment" ||
    processingStatus?.engine_type === "lyrics_alignment";
  const isActivelyProcessing =
    !isLyricsOnlyProcessing &&
    (processingStatus?.status === "queued" ||
      processingStatus?.status === "processing");

  const songActions = useSongActions(song, {}, sessionId);
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

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    dialogs.openDialog("details");
  };

  const showAction = (action: string) => actions.includes(action as "details" | "queue");

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
          <SongInfo song={song} showArtist={showArtist} />
        </div>
      </CardContent>

      <div className="flex items-center justify-around">
        <Button
          variant="ghost"
          size="icon"
          className="text-accent size-7"
          aria-label="Add to karaoke queue"
          onClick={showAction("queue") ? handleQueueClick : undefined}
          disabled={isActivelyProcessing}
        >
          <ListPlus className="size-5" />
        </Button>

        {showAction("details") && (
          <Button
            variant="ghost"
            size="icon"
            className="text-foreground p-2 size-6"
            aria-label="Song details"
            onClick={handleDetailsClick}
          >
            <MoreVertical className="size-5" />
          </Button>
        )}
      </div>

      <SongManagementDialog
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
    </Card>
  );
};

export default SongCard;
