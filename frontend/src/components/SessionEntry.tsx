import React, { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { useAuthStore } from "@/stores/authStore";
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
import { AlertCircle, Camera, Keyboard, LogOut } from "lucide-react";
import { LoginForm } from "@/components/auth/LoginForm";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:session-entry");
import { toast } from "sonner";

interface SessionEntryProps {
  redirectTo?: string;
}

const SessionEntry: React.FC<SessionEntryProps> = ({
  redirectTo = "/stage",
}) => {
  const [searchParams] = useSearchParams();
  const [sessionCode, setSessionCode] = useState(
    () => searchParams.get("code")?.toUpperCase().slice(0, 4) || "",
  );
  const [displayName, setDisplayName] = useState(() => {
    // Load saved name from localStorage on mount
    return localStorage.getItem("karaokeDisplayName") || "";
  });

  const [showHostLogin, setShowHostLogin] = useState(false);

  const {
    sessionId,
    isConnecting,
    connectionError,
    createSession,
    joinSession,
    clearSession,
  } = useSessionStore();

  const { isAuthenticated, user, logout } = useAuthStore();

  const codeFromUrl = searchParams.get("code")?.toUpperCase().slice(0, 4);

  // Clear any connection errors when component mounts
  useEffect(() => {
    if (connectionError) {
      clearSession();
    }
  }, [connectionError, clearSession]);

  // Auto-join when code is in the URL and user has a saved display name
  useEffect(() => {
    if (
      codeFromUrl?.length === 4 &&
      displayName.trim() &&
      !sessionId &&
      !isConnecting
    ) {
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
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redirect if already in a session
  if (sessionId) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleCreateSession = async () => {
    if (!isAuthenticated) {
      setShowHostLogin(true);
      return;
    }

    try {
      await createSession("stage");
    } catch (error) {
      logger.error("Failed to create session:", error);
      toast.error("Failed to create session. Please try again.");
    }
  };

  const handleLoginSuccess = async () => {
    setShowHostLogin(false);
    try {
      await createSession("stage");
    } catch (error) {
      logger.error("Failed to create session after login:", error);
      toast.error("Failed to create session. Please try again.");
    }
  };

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
      <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-orange-peel p-8 max-w-md w-full relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-heading text-rust mb-2">
            Open Karaoke Studio
          </h1>
          <p className="text-muted-foreground">
            Join or create a karaoke session
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

        {/* Create Session */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Create New Session</CardTitle>
            <CardDescription>
              {isAuthenticated
                ? `Logged in as ${user?.displayName || "Host"}`
                : "Host login required to create a session"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {showHostLogin && !isAuthenticated ? (
              <LoginForm onSuccess={handleLoginSuccess} />
            ) : (
              <Button
                onClick={handleCreateSession}
                disabled={isConnecting}
                variant="primary"
                className="w-full"
              >
                {isConnecting ? "Creating..." : "Create Session as Host"}
              </Button>
            )}
            {isAuthenticated && (
              <Button
                onClick={logout}
                variant="ghost"
                size="sm"
                className="w-full text-muted-foreground"
              >
                <LogOut className="h-3 w-3 mr-1" />
                Log out
              </Button>
            )}
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
      </div>
    </div>
  );
};

export default SessionEntry;
