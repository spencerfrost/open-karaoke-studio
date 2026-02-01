import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
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
import { AlertCircle } from "lucide-react";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:session-entry");
import { toast } from "sonner";

interface SessionEntryProps {
  redirectTo?: string;
}

const SessionEntry: React.FC<SessionEntryProps> = ({
  redirectTo = "/stage",
}) => {
  const [sessionCode, setSessionCode] = useState("");
  const [displayName, setDisplayName] = useState(() => {
    // Load saved name from localStorage on mount
    return localStorage.getItem("karaokeDisplayName") || "";
  });

  const {
    sessionId,
    isConnecting,
    connectionError,
    createSession,
    joinSession,
    clearSession,
  } = useSessionStore();

  // Clear any connection errors when component mounts
  useEffect(() => {
    if (connectionError) {
      clearSession();
    }
  }, [connectionError, clearSession]);

  // Redirect if already in a session
  if (sessionId) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleCreateSession = async () => {
    try {
      // Creating a session implies host role (stage), no display name needed
      await createSession("stage");
    } catch (error) {
      logger.error("Failed to create session:", error);
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
            <CardDescription>Enter a 4-character session code</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sessionCode">Session Code</Label>
              <Input
                id="sessionCode"
                type="text"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                placeholder="ABCD"
                maxLength={4}
                className="uppercase text-center text-lg tracking-widest"
              />
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
                isConnecting || sessionCode.length !== 4 || !displayName.trim()
              }
              variant="accent"
              className="w-full"
            >
              {isConnecting ? "Joining..." : "Join Session"}
            </Button>
          </CardContent>
        </Card>

        {/* Create Session */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Create New Session</CardTitle>
            <CardDescription>Start a new karaoke session</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleCreateSession}
              disabled={isConnecting}
              variant="primary"
              className="w-full"
            >
              {isConnecting ? "Creating..." : "Create Session as Host"}
            </Button>
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
