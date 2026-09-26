import React from "react";
import { useSessionConnection } from "@/features/session";
import { useSessionStore } from "@/stores/sessionStore";
import PerformanceControlsPanel from "./PerformanceControlsPanel";

/**
 * Component that handles WebSocket connection and renders performance controls.
 * RequireCapability({session: true}) guarantees a session exists before this
 * mounts (see routes/guards.tsx), so there is nothing to gate here beyond the
 * connecting state.
 */
export const ConnectedPerformanceControls: React.FC = () => {
  const { sessionId } = useSessionStore();
  const { connected } = useSessionConnection();

  const showConnecting = sessionId && !connected;

  if (showConnecting) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-orange-peel mb-4"></div>
        <p className="text-lg text-lemon-chiffon">
          Connecting to performance controls...
        </p>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <PerformanceControlsPanel />
    </div>
  );
};
