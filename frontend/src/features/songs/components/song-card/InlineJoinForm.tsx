import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSessionStore } from "@/stores/sessionStore";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:inline-join-form");

interface InlineJoinFormProps {
  onJoinSuccess: (singerName: string) => void;
  songTitle: string;
}

export const InlineJoinForm: React.FC<InlineJoinFormProps> = ({
  onJoinSuccess,
  songTitle,
}) => {
  const [singerName, setSingerName] = useState("");
  const [sessionCode, setSessionCode] = useState("");
  const { joinSession, isConnecting, connectionError } = useSessionStore();

  const isFormValid = singerName.trim().length > 0 && sessionCode.length === 4;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    try {
      await joinSession(
        sessionCode.toUpperCase(),
        "controller",
        singerName.trim(),
      );
      onJoinSuccess(singerName.trim());
    } catch (error) {
      logger.error("Failed to join session:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Join the session to add &ldquo;{songTitle}&rdquo; to the queue
      </p>

      <div className="space-y-1.5">
        <Label htmlFor="inline-singer-name" className="text-xs">
          Your Name
        </Label>
        <Input
          id="inline-singer-name"
          type="text"
          placeholder="Enter your name"
          value={singerName}
          onChange={(e) => setSingerName(e.target.value)}
          autoFocus
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="inline-session-code" className="text-xs">
          Session Code
        </Label>
        <Input
          id="inline-session-code"
          type="text"
          placeholder="ABCD"
          value={sessionCode}
          onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
          maxLength={4}
          className="font-mono text-center tracking-widest"
        />
      </div>

      {connectionError && (
        <div className="p-2 bg-destructive/10 border border-destructive/30 rounded-md">
          <p className="text-destructive text-xs">{connectionError}</p>
        </div>
      )}

      <Button
        type="submit"
        disabled={!isFormValid || isConnecting}
        className="w-full"
      >
        {isConnecting ? "Joining..." : "Join & Add to Queue"}
      </Button>
    </form>
  );
};
