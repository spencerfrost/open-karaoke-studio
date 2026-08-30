import React, { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useAccess, type Access } from "@/hooks/useAccess";
import { createLogger } from "@/lib/logger";

const logger = createLogger("routes:guards");

const RecoveringSpinner: React.FC = () => (
  <div className="min-h-screen bg-card text-card-foreground flex items-center justify-center">
    <div className="vintage-texture-overlay" />
    <div className="text-center space-y-4 relative z-10">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
      <p className="text-muted-foreground">Recovering session...</p>
    </div>
  </div>
);

/**
 * RequireAccess - the app-wide gate. Everything except /join sits behind
 * this: an account or a session, nothing more specific. Capability checks
 * (host, admin, session membership, device type) are a separate, inner
 * layer - see RequireCapability below.
 */
export const RequireAccess: React.FC = () => {
  const access = useAccess();
  const location = useLocation();

  if (access.isRecovering) {
    return <RecoveringSpinner />;
  }

  if (!access.canEnter) {
    return <Navigate to="/join" state={{ from: location }} replace />;
  }

  return <Outlet />;
};

export interface CapabilityRequirement {
  /** Any signed-in account - the account card is the point. */
  account?: boolean;
  /** A host or admin account. Does not require a session. */
  host?: boolean;
  admin?: boolean;
  /** A live session (any role). */
  session?: boolean;
  /** Bounces a device on the wrong side of a live session, silently. */
  device?: "stage" | "performer";
}

interface Redirect {
  to: string;
  message?: string;
}

function computeRedirect(
  access: Access,
  requirement: CapabilityRequirement,
): Redirect | null {
  if (requirement.account && !access.isAuthenticated) {
    return { to: "/", message: "Sign in to manage your account." };
  }
  if (requirement.host && !access.isHost) {
    return { to: "/", message: "Hosting a night needs a host account." };
  }
  if (requirement.admin && !access.isAdmin) {
    return { to: "/", message: "Admin access required." };
  }
  if (requirement.session && !access.inSession) {
    return {
      to: "/",
      message: "No session running yet — open the Stage to start one.",
    };
  }
  if (requirement.device === "performer" && access.isStageDevice) {
    return { to: "/stage" };
  }
  if (requirement.device === "stage" && !access.isStageDevice) {
    return { to: "/controls" };
  }
  return null;
}

/**
 * RequireCapability - the per-route requirement layered on top of
 * RequireAccess. Assumes the outer gate has already passed: a capability
 * failure sends the visitor to "/", never back to "/join" - they already
 * have an account or a session, just not the right one for this route.
 */
export const RequireCapability: React.FC<CapabilityRequirement> = (
  requirement,
) => {
  const access = useAccess();
  const redirect = access.isRecovering
    ? null
    : computeRedirect(access, requirement);
  const redirectTo = redirect?.to ?? null;
  const redirectMessage = redirect?.message ?? null;

  useEffect(() => {
    if (redirectMessage) {
      logger.info("Capability redirect:", { to: redirectTo, message: redirectMessage });
      toast.error(redirectMessage);
    }
  }, [redirectTo, redirectMessage]);

  if (access.isRecovering) {
    return <RecoveringSpinner />;
  }

  if (redirect) {
    return <Navigate to={redirect.to} replace />;
  }

  return <Outlet />;
};
