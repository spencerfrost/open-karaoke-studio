import React from "react";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import WebSocketStatus from "./WebsocketStatus";
import EndSessionButton from "./EndSessionButton";

const SessionStatusHeader: React.FC = () => {
  const { sessionId, displayCode, isSessionOwner } = useSessionStore();
  const { isPlaying, connected } = useKaraokePlayerStore();

  return (
    <div className="flex justify-between items-center mb-6 z-10">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold text-orange-peel font-accent tracking-[0.05em]">
          Performance Controls
        </h1>
        {sessionId && displayCode && (
          <div className="text-sm text-lemon-chiffon bg-overlay/40 rounded px-2 py-1">
            Session: {displayCode} {isSessionOwner ? "(Host)" : ""}
          </div>
        )}
        <div>
          <pre className="text-xs text-lemon-chiffon bg-overlay/40 rounded px-2 py-1 max-w-xs overflow-x-auto">
            {isPlaying ? "Playing" : "Paused"}
          </pre>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <EndSessionButton />
        <WebSocketStatus connected={connected} />
      </div>
    </div>
  );
};

export default SessionStatusHeader;
