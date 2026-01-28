import { useEffect } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSessionStore } from "@/stores/sessionStore";

/**
 * Hook for managing WebSocket connection to performance controls
 * Automatically connects/disconnects based on session state
 */
export const useSessionConnection = () => {
  const { sessionId, isConnected: sessionConnected } = useSessionStore();
  const { connect, disconnect, connected } = useKaraokePlayerStore();

  useEffect(() => {
    // Only connect to performance controls if we have a session
    if (sessionId && sessionConnected) {
      connect();
      return () => {
        disconnect();
      };
    }
  }, [connect, disconnect, sessionId, sessionConnected]);

  return {
    connected,
    sessionId,
    sessionConnected,
  };
};
