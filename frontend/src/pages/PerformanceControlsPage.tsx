import React from "react";
import { useSessionStore } from "@/stores/sessionStore";
import AppLayout from "@/components/layout/AppLayout";
import { SessionRecoveryLoading } from "@/features/session";
import { ConnectedPerformanceControls } from "@/features/performance";

/**
 * Mobile-optimized dedicated page for performance controls
 * Allows performers to control their performance settings from their mobile device
 * Uses session-based controls for proper isolation between karaoke sessions
 */
const PerformanceControlsPage: React.FC = () => {
  // RequireCapability({session: true}) already recovers and gates on a
  // session at boot (SessionProvider) before this page can mount, so
  // isRecovering here should always be false - kept as a defensive render
  // branch, not a second recovery trigger.
  const { isRecovering } = useSessionStore();

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
        {renderContent()}
      </div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
