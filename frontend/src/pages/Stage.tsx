/**
 * Stage - the TV, and the only place a session is born.
 *
 * The page owns the session and the queue; `StageShell` owns everything the
 * screen does with them. Deliberately no `AppLayout`: stage mode is a
 * full-screen app, not a page with a phone-sized nav bar pinned to the bottom
 * of a screen someone is looking at from across the room.
 */

import React, { useEffect, useRef } from "react";
import { StageShell } from "@/features/stage";
import { LoginForm } from "@/components/auth/LoginForm";
import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";

const logger = createLogger("page:stage");

const StageFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    className="relative flex h-screen w-full flex-col items-center justify-center gap-6 overflow-hidden p-6"
    style={{ background: "var(--page-bg)" }}
  >
    <div className="vintage-sunburst-pattern" />
    <div className="vintage-texture-overlay" />
    <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-6">
      {children}
    </div>
  </div>
);

const Stage: React.FC = () => {
  const {
    displayCode,
    joinAsHost,
    recoverSession,
    isRecovering,
    recoveryError,
    isConnecting,
    connectionError,
  } = useSessionStore();
  const { isAuthenticated } = useAuthStore();

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

  // Entering stage mode is the one and only thing that starts a session, so
  // this effect is the app's single creation path. `joinAsHost` hits the
  // idempotent get-or-create endpoint, so a re-entry resumes the same night.
  //
  // Once per mount, strictly: *entering* the stage starts a session, and ending
  // one from the exit prompt clears `displayCode` while this page is still up.
  // Without the guard that reads as "no session, better make one" and the night
  // you just ended immediately comes back with a new code.
  const hasBootstrapped = useRef(false);
  useEffect(() => {
    const initializeSession = async () => {
      if (hasBootstrapped.current || !isAuthenticated) return;
      hasBootstrapped.current = true;
      if (displayCode) return;

      try {
        await recoverSession();

        const state = useSessionStore.getState();
        if (!state.displayCode) {
          await joinAsHost();
        }
      } catch (error) {
        logger.error("Failed to initialize session:", error);
        toast.error("Failed to initialize session");
      }
    };

    initializeSession();
  }, [displayCode, isAuthenticated, recoverSession, joinAsHost]);

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

  // Running the stage means owning the night, and the server only hands a
  // session to a host account.
  if (!isAuthenticated && !displayCode) {
    return (
      <StageFrame>
        <div className="text-center">
          <h1 className="font-display text-4xl font-bold text-primary">
            Start a session
          </h1>
          <p className="pt-2 text-lg text-muted-foreground">
            Sign in as the host to open the stage.
          </p>
        </div>
        <div className="w-full">
          <LoginForm />
        </div>
      </StageFrame>
    );
  }

  // Show loading state during session recovery or creation
  if (isRecovering || (isConnecting && !displayCode)) {
    return (
      <StageFrame>
        <h1 className="text-center text-4xl font-bold text-primary">
          {isRecovering ? "Restoring Session" : "Creating Session"}
        </h1>
        <p className="max-w-md text-center text-xl text-muted-foreground">
          {isRecovering
            ? "Reconnecting to your existing karaoke session..."
            : "Setting up your karaoke session..."}
        </p>
        {(recoveryError || connectionError) && (
          <div className="text-center text-destructive">
            {recoveryError || connectionError}
          </div>
        )}
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
      </StageFrame>
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
    <div className="h-screen w-full overflow-hidden">
      <StageShell
        songId={currentSong?.id || ""}
        current={currentQueueItem}
        upcoming={queueQuery.data?.upcoming || []}
        queueItems={queueQuery.data?.items}
        onPlayFromQueue={handlePlayFromQueue}
        onRemoveFromQueue={handleRemoveFromQueue}
      />
    </div>
  );
};

export default Stage;
