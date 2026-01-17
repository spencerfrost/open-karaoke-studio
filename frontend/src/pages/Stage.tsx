import React, { useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { KaraokeQueueList } from "@/features/queue";
import { KaraokePlayer } from "@/features/player";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

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
    // This handler now receives the full queue data from the WebSocket
    const handleQueueUpdate = (data: { items?: any[] }) => {
      if (data.items) {
        console.log("Queue updated via WebSocket, updating cache directly.");
        // Update the React Query cache by refetching
        queueQuery.refetch();
      } else {
        // Fallback for older message formats or simple triggers
        console.log("Queue update notification received, refetching queue data.");
        queueQuery.refetch();
      }
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
      // Backend now automatically broadcasts updates, no need to notify manually
    } catch (error) {
      console.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      await playFromQueueMutation.mutateAsync(id);
      // Backend now automatically broadcasts updates, no need to notify manually
    } catch (error) {
      console.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 min-h-full p-6 relative items-center z-20">
        {/* Back button (to libary) */}
        <Button
          onClick={() => window.history.back()}
          className="absolute *:top-2 left-6"
          variant="ghost"
          aria-label="Back to library"
        >
          <svg
            className="w-6 h-6 text-orange-peel"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </Button>

        <KaraokePlayer 
          songId={currentSong?.id || ""}
          queueItems={queueQuery.data}
        />
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
