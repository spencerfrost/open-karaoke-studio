import React, { useRef, useState } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSessionStore } from "@/stores/sessionStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { generateSessionPlaylist } from "@/services/api";
import { createLogger } from "@/lib/logger";
import SessionEndModal from "./SessionEndModal";

const logger = createLogger("component:end-session-button");

interface EndSessionButtonProps {
  className?: string;
}

const EndSessionButton: React.FC<EndSessionButtonProps> = ({ className }) => {
  const { sessionId, isHost, clearSession } = useSessionStore();
  const [showModal, setShowModal] = useState(false);
  // Capture sessionId before clearSession() wipes it from the store
  const endedSessionId = useRef<string | null>(null);

  if (!sessionId || !isHost) return null;

  const handleEndSession = async () => {
    endedSessionId.current = sessionId;

    try {
      await fetch(`/api/sessions/${sessionId}/leave`, { method: "POST" });
    } catch (err) {
      logger.warn("Failed to notify server of session end:", err);
    }

    // Trigger playlist generation (fire and forget — modal will poll for result)
    generateSessionPlaylist(sessionId).catch((err) =>
      logger.warn("Failed to trigger playlist generation:", err),
    );

    setShowModal(true);
  };

  const handleModalClose = () => {
    setShowModal(false);
    sessionWebSocketService.disconnect();
    clearSession();
  };

  return (
    <>
      <Button
        variant="destructive"
        size="sm"
        onClick={handleEndSession}
        className={className}
      >
        <LogOut className="h-4 w-4 mr-2" />
        End Session
      </Button>

      {endedSessionId.current && (
        <SessionEndModal
          sessionId={endedSessionId.current}
          isOpen={showModal}
          onClose={handleModalClose}
        />
      )}
    </>
  );
};

export default EndSessionButton;
