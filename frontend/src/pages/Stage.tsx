import React, { useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { StageLayout } from "@/features/player/components/stage";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";

const logger = createLogger("page:stage");

const Stage: React.FC = () => {
  const {
    displayCode,
    createSession,
    recoverSession, // Changed from recoverHostSession
    isRecovering,
    recoveryError,
    isConnecting,
    connectionError,
  } = useSessionStore();

  const { useSong } = useSongs();

  // API hooks - must be called before any conditional returns
  const queueQuery = useQueue(displayCode || undefined);
  const removeFromQueueMutation = useRemoveFromKaraokeQueue(
    displayCode || undefined,
  );
  const playFromQueueMutation = usePlayFromKaraokeQueue(
    displayCode || undefined,
  );

  // Get the current loaded song from explicit queue state
  const currentQueueItem = queueQuery.data?.current;
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
          logger.error("Failed to initialize session:", error);
          toast.error("Failed to initialize session");
        }
      }
    };

    initializeSession();
  }, [displayCode, recoverSession, createSession]);

  // WebSocket effect for queue updates using unified session WebSocket
  useEffect(() => {
    // This handler now receives the full queue data from the WebSocket
    const handleQueueUpdate = (data: {
      current?: unknown;
      upcoming?: unknown[];
      items?: unknown[];
    }) => {
      if (data.items || data.current || data.upcoming) {
        logger.debug("Queue updated via WebSocket, updating cache directly.");
        // Update the React Query cache by refetching
        queueQuery.refetch();
      } else {
        // Fallback for older message formats or simple triggers
        logger.debug(
          "Queue update notification received, refetching queue data.",
        );
        queueQuery.refetch();
      }
    };

    const handleQueueJoined = (data: { room?: string } = {}) => {
      logger.debug("Joined queue room:", data?.room);
      // Request initial queue state
      sessionWebSocketService.requestQueueUpdate();
    };

    // Set up WebSocket event listeners using unified session service
    const cleanupJoined = sessionWebSocketService.on(
      "queue_joined",
      handleQueueJoined,
    );
    const cleanupUpdated = sessionWebSocketService.on(
      "queue_updated",
      handleQueueUpdate,
    );

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
              : "Setting up your karaoke session..."}
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
      logger.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      await playFromQueueMutation.mutateAsync(id);
      // Backend now automatically broadcasts updates, no need to notify manually
    } catch (error) {
      logger.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

  return (
    <AppLayout contentClassName="">
      <StageLayout
        songId={currentSong?.id || ""}
        current={currentQueueItem}
        upcoming={queueQuery.data?.upcoming || []}
        queueItems={queueQuery.data?.items}
        onPlayFromQueue={handlePlayFromQueue}
        onRemoveFromQueue={handleRemoveFromQueue}
      />
    </AppLayout>
  );
};

export default Stage;
