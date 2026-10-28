/**
 * Stage - the TV, and the only place a session is born.
 *
 * The page owns the session and the queue; `StageShell` owns everything the
 * screen does with them. Deliberately no `AppLayout`: stage mode is a
 * full-screen app, not a page with a phone-sized nav bar pinned to the bottom
 * of a screen someone is looking at from across the room.
 */

import React, { useEffect, useRef, useState } from "react";
import { StageShell } from "@/features/stage";
import CreateSessionScreen from "@/features/stage/screens/CreateSessionScreen";
import { cn } from "@/lib/utils";
import { useSongs } from "@/hooks/api/useSongs";
import {
  ExistingSessionError,
  useSessionStore,
  type HostSessionSetup,
} from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import type { SessionTurn } from "@/types/KaraokeQueue";

const logger = createLogger("page:stage");

/** Before the first queue payload lands there is nothing to hand off to. */
const NO_TURN: SessionTurn = {
  kind: "open",
  performerId: null,
  performerName: null,
  itemId: null,
  circle: [],
};

const StageFrame: React.FC<{
  children: React.ReactNode;
  /** Widened for the create screen's form; the loading states keep max-w-md. */
  contentClassName?: string;
}> = ({ children, contentClassName = "max-w-md" }) => (
  <div
    className="relative flex h-dvh w-full flex-col items-center justify-center gap-6 overflow-hidden p-6"
    style={{ background: "var(--page-bg)" }}
  >
    <div className="theme-pattern" />
    <div className="theme-texture" />
    {/* The scrim that makes stage mode dark. StageShell paints the same one, and
        without it these pre-session screens sit on the raw sunburst - blazing
        orange, and light-on-dark text tokens land on a light ground. */}
    <div className="absolute inset-0 z-[11] bg-overlay/85" />
    <div
      className={cn(
        "relative z-20 flex w-full flex-col items-center gap-6",
        contentClassName,
      )}
    >
      {children}
    </div>
  </div>
);

const Stage: React.FC = () => {
  const {
    displayCode,
    joinAsHost,
    recoverSession,
    resumeAccountHostSession,
    isRecovering,
    isResumingAccountSession,
    recoveryError,
    isConnecting,
    connectionError,
    sessionInfo,
  } = useSessionStore();
  const { isAuthenticated, user, expireSession } = useAuthStore();
  const isDemo = Boolean(user?.isDemo);

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

  // Entering stage mode only *resumes* a night; starting one is a decision the
  // host makes on CreateSessionScreen, which renders below when recovery comes
  // back empty. Recovery asks the server as well as this browser's storage: a
  // live session this browser has no record of is still tonight's session.
  //
  // Once per mount, strictly: ending a session from the exit prompt clears
  // `displayCode` while this page is still up. Without the guard that reads as
  // "no session, better go recover one" on every subsequent render.
  const hasBootstrapped = useRef(false);
  // Set once recovery has had its say, so "no session" means none to resume.
  const [hasInitialized, setHasInitialized] = useState(false);
  useEffect(() => {
    const initializeSession = async () => {
      if (hasBootstrapped.current || !isAuthenticated) return;
      hasBootstrapped.current = true;
      if (displayCode) {
        setHasInitialized(true);
        return;
      }

      try {
        await recoverSession();
        if (!useSessionStore.getState().sessionId) {
          await resumeAccountHostSession();
        }
      } catch (error) {
        logger.error("Failed to initialize session:", error);
        toast.error("Failed to initialize session");
      } finally {
        setHasInitialized(true);
      }
    };

    initializeSession();
  }, [displayCode, isAuthenticated, recoverSession, resumeAccountHostSession]);

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

  // A demo account never starts a session here: its one session came from
  // Try it live, and the server refuses another. Once that session is gone,
  // sign the visitor out, which sends them back to the start page.
  const demoIsOver =
    isDemo &&
    hasInitialized &&
    !displayCode &&
    !isRecovering &&
    !isResumingAccountSession &&
    !isConnecting;
  // Nothing tells the stage when a session simply runs out, so a demo stage
  // ends itself at the session's expiry rather than carrying on without one.
  const sessionExpiresAt = sessionInfo?.expires_at;
  useEffect(() => {
    if (!isDemo || !sessionExpiresAt) return;
    // The server sends naive UTC timestamps.
    const hasOffset = /(Z|[+-]\d\d:\d\d)$/.test(sessionExpiresAt);
    const expiresMs = Date.parse(
      hasOffset ? sessionExpiresAt : `${sessionExpiresAt}Z`,
    );
    if (Number.isNaN(expiresMs)) return;
    const timer = window.setTimeout(
      () => useSessionStore.getState().clearSession(),
      Math.max(expiresMs - Date.now(), 0),
    );
    return () => window.clearTimeout(timer);
  }, [isDemo, sessionExpiresAt]);

  useEffect(() => {
    if (demoIsOver) {
      logger.info("Demo session is over; signing the demo account out");
      expireSession();
    }
  }, [demoIsOver, expireSession]);

  const handleStartSession = async (options: HostSessionSetup) => {
    try {
      await joinAsHost(options);
    } catch (error) {
      // The create screen asks the host what to do about a live session.
      if (error instanceof ExistingSessionError) throw error;
      logger.error("Failed to start session:", error);
      toast.error("Failed to start session");
    }
  };

  // Show loading state while recovery decides whether there's a night to resume.
  if (isRecovering || isResumingAccountSession) {
    return (
      <StageFrame>
        <h1 className="text-center text-4xl font-bold text-primary">
          Restoring Session
        </h1>
        <p className="max-w-md text-center text-xl text-muted-foreground">
          Reconnecting to your existing karaoke session...
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

  // Never the create screen for a demo: a spinner until recovery has run,
  // then a line to read while the sign-out above sends them back.
  if (!displayCode && isDemo) {
    return (
      <StageFrame>
        {hasInitialized ? (
          <h1 className="text-center text-4xl font-bold text-primary">
            Your demo has ended
          </h1>
        ) : (
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        )}
      </StageFrame>
    );
  }

  // Nothing to resume - ask before creating one. The screen owns the whole
  // creating-a-session moment, spinner included: routing `isConnecting` through
  // a branch up here instead would unmount it mid-request and throw away every
  // name the host just typed if the create failed.
  if (!displayCode) {
    return (
      <StageFrame contentClassName="max-w-2xl">
        <CreateSessionScreen
          onStart={handleStartSession}
          isStarting={isConnecting}
        />
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
    <div className="h-dvh w-full overflow-hidden">
      <StageShell
        songId={currentSong?.id || ""}
        current={currentQueueItem}
        upcoming={queueQuery.data?.upcoming || []}
        turn={queueQuery.data?.turn ?? NO_TURN}
        onPlayFromQueue={handlePlayFromQueue}
        onRemoveFromQueue={handleRemoveFromQueue}
      />
    </div>
  );
};

export default Stage;
