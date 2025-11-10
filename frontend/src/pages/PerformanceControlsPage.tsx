import React, { useEffect } from "react";
import { useSessionStore } from "@/stores/sessionStore";
import AppLayout from "@/components/layout/AppLayout";
import { SessionStatusHeader, SessionRecoveryLoading } from "@/features/session";
import { ConnectedPerformanceControls } from "@/features/performance";

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

    // Always show the performance controls (with join dialog overlay if needed)
    return <ConnectedPerformanceControls />;
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
