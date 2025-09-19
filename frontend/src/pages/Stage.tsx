import React, { useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KaraokeQueueList from "@/components/karaoke-queue/KaraokeQueueList";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";

const Stage: React.FC = () => {
  const { 
    displayCode, 
    createSession, 
    recoverSession,  // Changed from recoverHostSession
    isRecovering, 
    recoveryError,
    isConnecting,
    connectionError 
  } = useSessionStore();

  const { useSong } = useSongs();

  // API hooks - must be called before any conditional returns
  const queueQuery = useQueue(displayCode || undefined);
  const removeFromQueueMutation = useRemoveFromKaraokeQueue(displayCode || undefined);
  const playFromQueueMutation = usePlayFromKaraokeQueue(displayCode || undefined);

  // Get the current song (position 0) from the queue
  const currentQueueItem = queueQuery.data?.find((item) => item.position === 0);
  const currentSongId = currentQueueItem?.song?.id;
  const { data: currentSong } = useSong(currentSongId ?? "");

  // Recover existing host session or create new one on mount
  useEffect(() => {
    const initializeSession = async () => {
      if (!displayCode) {
        try {
          // First try to recover existing session (host or performer)
          await recoverSession();
          
          // If recovery didn't work (no stored session), create new host session
          const state = useSessionStore.getState();
          if (!state.displayCode) {
            await createSession("stage");
          }
        } catch (error) {
          console.error("Failed to initialize session:", error);
          toast.error("Failed to initialize session");
        }
      }
    };

    initializeSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // WebSocket effect for queue updates using unified session WebSocket
  useEffect(() => {
    const handleQueueUpdate = () => {
      console.log("Queue updated via unified session WebSocket, refetching queue data");
      queueQuery.refetch();
    };

    const handleQueueJoined = (data: { room?: string } = {}) => {
      console.log("Joined queue room:", data?.room);
      // Request initial queue state
      sessionWebSocketService.requestQueueUpdate();
    };

    // Set up WebSocket event listeners using unified session service
    const cleanupJoined = sessionWebSocketService.on("queue_joined", handleQueueJoined);
    const cleanupUpdated = sessionWebSocketService.on("queue_updated", handleQueueUpdate);

    // Cleanup
    return () => {
      cleanupJoined();
      cleanupUpdated();
    };
  }, [queueQuery]);

  // Show loading state during session recovery or creation
  if (isRecovering || (isConnecting && !displayCode)) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-full gap-6">
          <h1 className="text-4xl font-bold text-orange-peel text-center">
            {isRecovering ? "Restoring Session" : "Creating Session"}
          </h1>
          <p className="text-xl text-center text-muted-foreground max-w-md">
            {isRecovering 
              ? "Reconnecting to your existing karaoke session..." 
              : "Setting up your karaoke session..."
            }
          </p>
          {(recoveryError || connectionError) && (
            <div className="text-center text-destructive">
              {recoveryError || connectionError}
            </div>
          )}
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-peel"></div>
          </div>
        </div>
      </AppLayout>
    );
  }

  const handleRemoveFromQueue = async (id: string) => {
    try {
      await removeFromQueueMutation.mutateAsync(id);
      // Notify unified WebSocket service about queue changes
      sessionWebSocketService.notifyQueueChanged();
      toast.success("Song removed from queue");
    } catch (error) {
      console.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      await playFromQueueMutation.mutateAsync(id);
      // Notify unified WebSocket service about queue changes
      sessionWebSocketService.notifyQueueChanged();
      toast.success("Song is being loaded...");
    } catch (error) {
      console.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 min-h-full p-6 relative z-20">

        <div className="aspect-video w-full max-w-[90vw] max-h-[90vh] bg-black/80 rounded-xl overflow-hidden">
          <KaraokePlayer
            songId={currentSong?.id || ""}
            size="full"
            autoPlay={false}
            controls={true}
            showInfo={true}
            showVisualizer={true}
          />
        </div>
        <h2 className="text-2xl font-semibold text-center my-4 text-orange-peel">
          Up Next
        </h2>

        <div className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden text-background border border-orange-peel">
          <KaraokeQueueList
            items={queueQuery.data || []}
            emptyMessage="No songs in the queue"
            onRemove={handleRemoveFromQueue}
            onPlay={handlePlayFromQueue}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default Stage;
