import React from "react";
import { Navigate } from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import SessionEntry from "@/components/SessionEntry";

interface SessionGuardProps {
  children: React.ReactNode;
  redirectTo?: string;
  requireSession?: boolean;
  deviceType?: "stage" | "performer";
}

const SessionGuard: React.FC<SessionGuardProps> = ({
  children,
  redirectTo,
  requireSession = true,
  deviceType,
}) => {
  const { sessionId, isRecovering, isHost } = useSessionStore();

  // Show loading while recovering session
  if (isRecovering) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="vintage-texture-overlay" />
        <div className="text-center space-y-4 relative z-10">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">Recovering session...</p>
        </div>
      </div>
    );
  }

  // If session is required but not present, show session entry
  if (requireSession && !sessionId) {
    return <SessionEntry redirectTo={redirectTo} />;
  }

  // Device type protection logic - redirect gracefully if user accesses wrong route directly
  if (sessionId && deviceType) {
    // Stage routes require host devices - redirect performers to controls
    if (deviceType === "stage" && !isHost) {
      console.info("Performer device redirected from stage route to controls");
      return <Navigate to="/controls" replace />;
    }

    // Performer routes require non-host devices - redirect hosts to stage
    if (deviceType === "performer" && isHost) {
      console.info("Host device redirected from performer route to stage");
      return <Navigate to="/stage" replace />;
    }
  }

  // Session is not required or is present with proper device type, render children
  return <>{children}</>;
};

export default SessionGuard;
