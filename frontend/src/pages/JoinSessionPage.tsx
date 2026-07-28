import { useState } from "react";
import { useSessionStore } from "../stores/sessionStore";

export default function JoinSessionPage() {
  const [sessionCode, setSessionCode] = useState("");
  const [deviceType, setDeviceType] = useState<
    "stage" | "performer" | "controller"
  >("performer");
  const { joinSession, isConnecting, connectionError, createSession } =
    useSessionStore();

  const handleJoin = async () => {
    if (!sessionCode.trim()) return;
    await joinSession(sessionCode.trim(), deviceType);
  };

  const handleCreate = async () => {
    await createSession(deviceType);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-2">Open Karaoke Studio</h1>
          <p className="text-foreground/60">Join a karaoke session</p>
        </div>

        <div className="space-y-6">
          {/* Create Session */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Create New Session</h2>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) =>
                  setDeviceType(
                    e.target.value as "stage" | "performer" | "controller",
                  )
                }
                className="w-full px-3 py-2 bg-input border border-glass-border/20 rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="stage">Stage (Host)</option>
                <option value="performer">Performer</option>
                <option value="controller">Controller</option>
              </select>
            </div>
            <button
              onClick={handleCreate}
              disabled={isConnecting}
              className="w-full bg-primary hover:bg-primary/90 disabled:bg-muted px-4 py-2 rounded-md font-medium transition-colors"
            >
              {isConnecting ? "Creating..." : "Create Session"}
            </button>
          </div>

          {/* Join Session */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Join Existing Session</h2>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Session Code</label>
              <input
                type="text"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                placeholder="Enter 4-character code"
                maxLength={4}
                className="w-full px-3 py-2 bg-input border border-glass-border/20 rounded-md focus:outline-none focus:ring-2 focus:ring-ring uppercase"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) =>
                  setDeviceType(
                    e.target.value as "stage" | "performer" | "controller",
                  )
                }
                className="w-full px-3 py-2 bg-input border border-glass-border/20 rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="performer">Performer</option>
                <option value="controller">Controller</option>
                <option value="stage">Stage (Host)</option>
              </select>
            </div>
            <button
              onClick={handleJoin}
              disabled={isConnecting || sessionCode.length !== 4}
              className="w-full bg-success hover:bg-success/90 disabled:bg-muted px-4 py-2 rounded-md font-medium transition-colors"
            >
              {isConnecting ? "Joining..." : "Join Session"}
            </button>
          </div>

          {/* Error Display */}
          {connectionError && (
            <div className="p-4 bg-destructive/20 border border-destructive/40 rounded-md">
              <p className="text-destructive">{connectionError}</p>
            </div>
          )}
        </div>

        <div className="text-center text-sm text-foreground/60">
          <p>
            Enter a 4-character session code to join an existing karaoke
            session,
          </p>
          <p>or create a new session to get started!</p>
        </div>
      </div>
    </div>
  );
}
