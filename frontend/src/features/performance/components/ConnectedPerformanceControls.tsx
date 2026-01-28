import React from "react";
import { useSessionConnection } from "@/features/session";
import { useSessionStore } from "@/stores/sessionStore";
import { JoinSessionDialog } from "@/features/songs/components/JoinSessionDialog";
import PerformanceControlsPanel from "./PerformanceControlsPanel";

/**
 * Component that handles WebSocket connection and renders performance controls
 * Shows join dialog overlay when not in session, preview controls underneath
 */
export const ConnectedPerformanceControls: React.FC = () => {
  const { sessionId } = useSessionStore();
  const { connected } = useSessionConnection();

  // Show join dialog overlay if not in a session
  const showJoinDialog = !sessionId;

  // Show connecting state when in session but not connected
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
      {/* Always show performance controls (with default values if not connected) */}
      <PerformanceControlsPanel />

      {/* Overlay join dialog when not in session */}
      {showJoinDialog && (
        <JoinSessionDialog
          isOpen={true}
          onClose={() => {}} // Uncloseable - user must join a session
          context="control the karaoke performance"
          onJoinSuccess={(name) => {
            console.log(`${name} joined as performer`);
          }}
        />
      )}
    </div>
  );
};
