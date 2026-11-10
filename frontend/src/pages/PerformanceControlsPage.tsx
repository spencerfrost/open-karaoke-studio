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
    // No nav: the panel has its own Close, and the faders need the height.
    // overscroll-none: no rubber-band bounce or pull-to-refresh when a drag
    // runs past the top or bottom of the page.
    <AppLayout hideNav contentClassName="p-2 sm:p-4 overscroll-none">
      {/* No page-wide touch-action: the fader cards block scrolling on
          themselves, and a short phone must still be able to scroll from
          the rest of the page. */}
      <div className="h-full flex flex-col">{renderContent()}</div>
    </AppLayout>
  );
};

export default PerformanceControlsPage;
