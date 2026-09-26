import React from "react";
import { Music2, ExternalLink, Loader2, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { QRCodeDisplay } from "@/features/queue";
import { createLogger } from "@/lib/logger";
import { useSessionPlaylist } from "../hooks/useSessionPlaylist";

const logger = createLogger("component:session-end-modal");

interface SessionEndModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

const SessionEndModal: React.FC<SessionEndModalProps> = ({
  sessionId,
  isOpen,
  onClose,
}) => {
  const { data, isLoading, isError } = useSessionPlaylist({
    sessionId,
    enabled: isOpen,
  });

  const isGenerating =
    isLoading || data?.status === "pending" || data?.status === "processing";
  const isReady = data?.status === "ready" && !!data.youtube_music_url;
  const isFailed = data?.status === "failed" || isError;

  logger.debug("SessionEndModal state:", { status: data?.status, isReady });

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Music2 className="h-5 w-5 text-orange-peel" />
            {isReady ? "Your Karaoke Night Playlist" : "Session Ended"}
          </DialogTitle>
          <DialogDescription>
            {isGenerating && "Generating your YouTube Music playlist…"}
            {isReady &&
              `${data.song_count} song${data.song_count !== 1 ? "s" : ""} from tonight's session`}
            {isFailed && "Session ended successfully."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-6 py-4">
          {isGenerating && (
            <div className="flex flex-col items-center gap-3 text-muted-foreground">
              <Loader2 className="h-10 w-10 animate-spin text-orange-peel" />
              <p className="text-sm">Creating playlist on YouTube Music…</p>
            </div>
          )}

          {isReady && data.youtube_music_url && (
            <>
              <QRCodeDisplay value={data.youtube_music_url} size={200} />
              <p className="text-sm text-muted-foreground text-center">
                Scan the QR code to open on your phone
              </p>
              <Button
                className="w-full"
                onClick={() =>
                  window.open(data.youtube_music_url, "_blank", "noopener")
                }
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open in YouTube Music
              </Button>
            </>
          )}

          {isFailed && (
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <AlertCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm text-center">
                {data?.error_message
                  ? `Couldn't generate playlist: ${data.error_message}`
                  : "Couldn't generate the playlist. You can try again later."}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="w-full">
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SessionEndModal;
