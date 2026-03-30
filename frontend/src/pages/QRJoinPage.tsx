import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSessionStore } from "../stores/sessionStore";
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

export default function QRJoinPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState(() => {
    return localStorage.getItem("karaokeDisplayName") || "";
  });
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
    localStorage.setItem("karaokeDisplayName", trimmedName);
    navigate("/");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && name.trim()) handleJoin();
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-orange-peel p-8 max-w-md w-full relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-heading text-rust">
            Open Karaoke Studio
          </h1>
        </div>

        <Card>
          <CardHeader className="text-center">
            <CardDescription>Joining session</CardDescription>
            <CardTitle className="text-4xl font-mono tracking-widest text-primary">
              {sessionCode}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Your name</Label>
              <Input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Enter your name"
                autoFocus
                maxLength={50}
              />
            </div>

            <Button
              onClick={handleJoin}
              disabled={isConnecting || !name.trim()}
              variant="accent"
              className="w-full"
            >
              {isConnecting ? "Joining..." : "Join Session"}
            </Button>

            {connectionError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{connectionError}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
