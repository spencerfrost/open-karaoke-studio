import React, { useEffect, useRef, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Camera, Keyboard } from "lucide-react";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:session-entry");
import { toast } from "sonner";

interface SessionEntryProps {
  redirectTo?: string;
}

/**
 * SessionEntry - how a performer gets into someone else's session.
 *
 * It used to double as the host's create-a-session screen, and auto-created one
 * on mount for any logged-in host. Sessions now begin in exactly one place -
 * entering stage mode - so this is the performer half only. Host login lives in
 * Settings.
 */
const SessionEntry: React.FC<SessionEntryProps> = ({
  redirectTo = "/controls",
}) => {
  const [searchParams] = useSearchParams();
  const [sessionCode, setSessionCode] = useState(
    () => searchParams.get("code")?.toUpperCase().slice(0, 4) || "",
  );
  const [displayName, setDisplayName] = useState(() => {
    // Load saved name from localStorage on mount
    return localStorage.getItem("karaokeDisplayName") || "";
  });

  const {
    sessionId,
    isConnecting,
    connectionError,
    joinSession,
    clearSession,
  } = useSessionStore();

  const codeFromUrl = searchParams.get("code")?.toUpperCase().slice(0, 4);

  // Clear any connection errors when component mounts
  useEffect(() => {
    if (connectionError) {
      clearSession();
    }
  }, [connectionError, clearSession]);

  const hasAutoJoined = useRef(false);

  // Auto-join when code is in the URL and user has a saved display name.
  // The ref guard ensures this fires at most once even if dependencies change.
  useEffect(() => {
    if (hasAutoJoined.current) return;
    if (
      codeFromUrl?.length === 4 &&
      displayName.trim() &&
      !sessionId &&
      !isConnecting
    ) {
      hasAutoJoined.current = true;
      logger.info("Auto-joining session from QR code", { code: codeFromUrl });
      joinSession(codeFromUrl, "performer", displayName.trim())
        .then(() =>
          localStorage.setItem("karaokeDisplayName", displayName.trim()),
        )
        .catch((error) => {
          logger.error("Auto-join failed:", error);
          toast.error("Failed to join session. Please try manually.");
        });
    }
  }, [codeFromUrl, displayName, sessionId, isConnecting, joinSession]);

  // Redirect if already in a session
  if (sessionId) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleJoinSession = async () => {
    if (!sessionCode.trim()) {
      toast.error("Please enter a session code");
      return;
    }

    if (!displayName.trim()) {
      toast.error("Please enter your name");
      return;
    }

    try {
      // Joining a session implies performer role
      await joinSession(
        sessionCode.trim().toUpperCase(),
        "performer",
        displayName.trim(),
      );
      // Save the name to localStorage for future sessions
      localStorage.setItem("karaokeDisplayName", displayName.trim());
    } catch (error) {
      logger.error("Failed to join session:", error);
      toast.error(
        "Failed to join session. Please check the code and try again.",
      );
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      <Card className="block p-8 rounded-lg shadow-xl border-orange-peel max-w-md w-full relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-bold text-rust mb-2">
            Open Karaoke Studio
          </h1>
          <p className="text-muted-foreground">
            Join the karaoke session on the stage screen
          </p>
        </div>

        {/* Join Session */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Join Karaoke Session</CardTitle>
            <CardDescription>
              Scan the QR code on the stage screen to join
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* QR Code - Primary */}
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="rounded-full bg-orange-peel/10 p-6">
                <Camera className="h-12 w-12 text-orange-peel" />
              </div>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">
                  or enter code manually
                </span>
              </div>
            </div>

            {/* Session Code - Secondary */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="sessionCode">Session Code</Label>
                <div className="relative">
                  <Keyboard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="sessionCode"
                    type="text"
                    value={sessionCode}
                    onChange={(e) =>
                      setSessionCode(e.target.value.toUpperCase())
                    }
                    placeholder="ABCD"
                    maxLength={4}
                    className="uppercase text-center text-lg tracking-widest pl-10"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="displayName">Your Name</Label>
                <Input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Enter your name"
                  maxLength={50}
                />
              </div>
              <Button
                onClick={handleJoinSession}
                disabled={
                  isConnecting ||
                  sessionCode.length !== 4 ||
                  !displayName.trim()
                }
                variant="accent"
                className="w-full"
              >
                {isConnecting ? "Joining..." : "Join Session"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error Display */}
        {connectionError && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{connectionError}</AlertDescription>
          </Alert>
        )}

        <div className="text-center text-sm text-muted-foreground">
          <p>
            All devices need to be in a session to use the karaoke features.
          </p>
        </div>
      </Card>
    </div>
  );
};

export default SessionEntry;
