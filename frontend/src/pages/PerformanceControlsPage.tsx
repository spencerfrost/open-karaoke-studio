import React, { useEffect } from "react";
import { useSessionStore } from "@/stores/sessionStore";
import AppLayout from "@/components/layout/AppLayout";
import SessionStatusHeader from "@/components/SessionStatusHeader";
import SessionJoinForm from "@/components/SessionJoinForm";
import SessionRecoveryLoading from "@/components/SessionRecoveryLoading";
import PerformanceControlsPanel from "@/components/PerformanceControlsPanel";
import { useSessionConnection } from "@/hooks/useSessionConnection";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses session-based controls for proper isolation between karaoke sessions
 */
const PerformanceControlsPage: React.FC = () => {
  // Session state
  const {
    sessionId,
    isRecovering,
    recoverSession,
  } = useSessionStore();

  // WebSocket connection
  const { connected } = useSessionConnection();

  useEffect(() => {
    // Try to recover existing session on page load
    if (!sessionId) {
      recoverSession();
    }
  }, [sessionId, recoverSession]);

  const renderContent = () => {
    // Show loading state during session recovery
    if (isRecovering) {
      return <SessionRecoveryLoading />;
    }

    // Show session join UI when not in a session
    if (!sessionId) {
      return <SessionJoinForm />;
    }

    // Show connecting state when in session but not connected
    if (!connected) {
      return (
        <div className="flex-1 flex items-center justify-center flex-col">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-orange-peel mb-4"></div>
          <p className="text-lg text-lemon-chiffon">
            Connecting to performance controls...
          </p>
        </div>
      );
    }

    // Show performance controls when connected
    return <PerformanceControlsPanel />;
  };

  return (
    <AppLayout>
      <div
        className="h-full flex flex-col"
        style={{ touchAction: "none" }} // Prevent dragging on mobile
      >
        <SessionStatusHeader />
        {renderContent()}
      </div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
