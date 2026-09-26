import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";

interface AuthSlice {
  isAuthenticated: boolean;
  user: {
    isAdmin: boolean;
    isHost: boolean;
    displayName: string | null;
  } | null;
}

interface SessionSlice {
  sessionId: string | null;
  displayName: string | null;
  isStageDevice: boolean;
  isSessionOwner: boolean;
  isRecovering: boolean;
}

export interface Access {
  isRecovering: boolean;
  isAuthenticated: boolean;
  /** user.isHost || user.isAdmin - admins can do anything a host can. */
  isHost: boolean;
  isAdmin: boolean;
  /** The one canonical "am I in a session" check - see hooks/useAccess.ts. */
  inSession: boolean;
  isStageDevice: boolean;
  isSessionOwner: boolean;
  /** Who to credit as the singer: the session's own name, else the account's. */
  singerName: string | null;
  /** The app-wide gate: everything except /join requires this. */
  canEnter: boolean;
}

/**
 * Pure evaluator behind useAccess() - kept separate so the access matrix can
 * be table-tested without mounting React or the Zustand stores.
 *
 * canEnter mirrors the backend's require_host_or_session_member
 * (backend/app/api/dependencies.py): ANY authenticated account clears the
 * gate, not just host/admin, because a Performer account tier is planned.
 * Do not narrow this to isHost || isAdmin.
 */
export function evaluateAccess(auth: AuthSlice, session: SessionSlice): Access {
  const isHost = Boolean(auth.user?.isHost || auth.user?.isAdmin);
  const isAdmin = Boolean(auth.user?.isAdmin);
  const inSession = session.sessionId !== null;

  return {
    isRecovering: session.isRecovering,
    isAuthenticated: auth.isAuthenticated,
    isHost,
    isAdmin,
    inSession,
    isStageDevice: session.isStageDevice,
    isSessionOwner: session.isSessionOwner,
    singerName: session.displayName ?? auth.user?.displayName ?? null,
    canEnter: auth.isAuthenticated || inSession,
  };
}

export function useAccess(): Access {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);
  const sessionId = useSessionStore((state) => state.sessionId);
  const displayName = useSessionStore((state) => state.displayName);
  const isStageDevice = useSessionStore((state) => state.isStageDevice);
  const isSessionOwner = useSessionStore((state) => state.isSessionOwner);
  const isRecovering = useSessionStore((state) => state.isRecovering);

  return evaluateAccess(
    { isAuthenticated, user },
    { sessionId, displayName, isStageDevice, isSessionOwner, isRecovering },
  );
}
