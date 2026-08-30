/**
 * ExitStagePrompt - leaving the stage is two different things, so it asks which.
 *
 * "End session" retires the night: the queue stops being live and the code is
 * handed back. "Keep running" is the escape hatch — drop out of full screen for
 * a minute to check something on the desktop, with the session, the socket and
 * the queue all still up, so walking back into stage mode resumes it.
 *
 * Note "Keep running" deliberately does NOT call `leaveSession()`: that would
 * deactivate this device's row on the server, which is the opposite of keeping
 * the TV in the session.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useSessionStore } from "@/stores/sessionStore";
import SessionEndModal from "@/features/session/components/SessionEndModal";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:exit-stage-prompt");

interface ExitStagePromptProps {
  isOpen: boolean;
  onClose: () => void;
  /** Drop out of full screen before navigating away from the stage. */
  onLeaveStage: () => void;
}

const ExitStagePrompt: React.FC<ExitStagePromptProps> = ({
  isOpen,
  onClose,
  onLeaveStage,
}) => {
  const navigate = useNavigate();
  const { sessionId, displayCode, isSessionOwner, endSession } =
    useSessionStore();
  const [endedSessionId, setEndedSessionId] = useState<string | null>(null);

  const handleKeepRunning = () => {
    onClose();
    onLeaveStage();
    navigate("/");
  };

  const handleEndSession = async () => {
    if (!sessionId) return;
    // Captured before endSession() wipes it from the store — the recap modal
    // needs it to poll for the generated playlist.
    setEndedSessionId(sessionId);
    onClose();

    try {
      await endSession();
    } catch (error) {
      logger.error("Failed to end session:", error);
      toast.error("Failed to end the session on the server.");
    }
  };

  const handleRecapClose = () => {
    setEndedSessionId(null);
    onLeaveStage();
    navigate("/");
  };

  return (
    <>
      <AlertDialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Leave stage mode?</AlertDialogTitle>
            <AlertDialogDescription>
              {isSessionOwner
                ? `Session ${displayCode ?? ""} can keep running while you step away — the queue and everyone's phones stay connected.`
                : "The session keeps running; this screen just stops being the stage."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2 sm:justify-between">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <div className="flex gap-2">
              <AlertDialogAction asChild>
                <Button variant="secondary" onClick={handleKeepRunning}>
                  Keep it running
                </Button>
              </AlertDialogAction>
              {isSessionOwner && (
                <AlertDialogAction asChild>
                  <Button variant="destructive" onClick={handleEndSession}>
                    End the session
                  </Button>
                </AlertDialogAction>
              )}
            </div>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {endedSessionId && (
        <SessionEndModal
          sessionId={endedSessionId}
          isOpen={true}
          onClose={handleRecapClose}
        />
      )}
    </>
  );
};

export default ExitStagePrompt;
