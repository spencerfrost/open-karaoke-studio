import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSessionStore } from "../stores/sessionStore";

export default function QRJoinPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const { joinSession, isConnecting, connectionError } = useSessionStore();

  if (!code) {
    navigate("/join", { replace: true });
    return null;
  }

  const sessionCode = code.toUpperCase();

  const handleJoin = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) return;
    await joinSession(sessionCode, "performer", trimmedName);
    navigate("/");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleJoin();
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="max-w-sm w-full space-y-8 p-8">
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-6">Open Karaoke Studio</p>
          <h1 className="text-2xl font-bold mb-1">Joining session</h1>
          <p className="text-4xl font-mono font-bold tracking-widest text-primary">
            {sessionCode}
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="name">
              Your name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter your name"
              autoFocus
              className="w-full px-3 py-2 bg-input border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary text-foreground"
            />
          </div>

          <button
            onClick={handleJoin}
            disabled={isConnecting || !name.trim()}
            className="w-full bg-primary hover:bg-primary/90 disabled:bg-muted text-primary-foreground px-4 py-2 rounded-md font-medium transition-colors"
          >
            {isConnecting ? "Joining..." : "Join Session"}
          </button>

          {connectionError && (
            <div className="p-4 bg-destructive/20 border border-destructive/50 rounded-md">
              <p className="text-destructive text-sm">{connectionError}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
