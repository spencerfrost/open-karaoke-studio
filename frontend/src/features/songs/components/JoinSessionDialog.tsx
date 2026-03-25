import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:join-session");
import { Label } from "@/components/ui/label";
import { useSessionStore } from "@/stores/sessionStore";

interface JoinSessionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onJoinSuccess?: (singerName: string) => void;
  context?: string; // Optional context for messaging
}

export const JoinSessionDialog: React.FC<JoinSessionDialogProps> = ({
  isOpen,
  onClose,
  onJoinSuccess,
  context = "join the karaoke session",
}) => {
  const [singerName, setSingerName] = useState("");
  const [sessionCode, setSessionCode] = useState("");

  const { joinSession, isConnecting, connectionError } = useSessionStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (singerName.trim() && sessionCode.length === 4) {
      try {
        await joinSession(
          sessionCode.toUpperCase(),
          "controller",
          singerName.trim(),
        );

        // Call success callback with the captured information
        onJoinSuccess?.(singerName.trim());

        // Reset form and close
        setSingerName("");
        setSessionCode("");
        onClose();
      } catch (error) {
        logger.error("Failed to join session:", error);
        // Error is handled by the session store
      }
    }
  };

  const handleClose = () => {
    setSingerName("");
    setSessionCode("");
    onClose();
  };

  const isFormValid = singerName.trim() && sessionCode.length === 4;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Join Karaoke Session</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="singer-name">Your Name</Label>
              <Input
                id="singer-name"
                type="text"
                placeholder="Enter your name"
                value={singerName}
                onChange={(e) => setSingerName(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="session-code">Session Code</Label>
              <Input
                id="session-code"
                type="text"
                placeholder="ABCD"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                maxLength={4}
                className="font-mono text-center"
              />
              <p className="text-sm text-muted-foreground">
                Enter the 4-character session code to {context}
              </p>
            </div>

            {connectionError && (
              <div className="p-3 bg-red-900/50 border border-red-700 rounded-md">
                <p className="text-red-200 text-sm">{connectionError}</p>
              </div>
            )}
          </div>
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!isFormValid || isConnecting}>
              {isConnecting ? "Joining..." : "Join Session"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
