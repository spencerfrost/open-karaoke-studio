import React from "react";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import WebSocketStatus from "./WebsocketStatus";
import EndSessionButton from "./EndSessionButton";

const SessionStatusHeader: React.FC = () => {
  const { sessionId, displayCode, isHost } = useSessionStore();
  const { isPlaying, connected } = useKaraokePlayerStore();

  return (
    <div className="flex justify-between items-center mb-6 z-10">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold text-orange-peel font-retro">
          Performance Controls
        </h1>
        {sessionId && displayCode && (
          <div className="text-sm text-lemon-chiffon bg-black/40 rounded px-2 py-1">
            Session: {displayCode} {isHost ? "(Host)" : ""}
          </div>
        )}
        <div>
          <pre className="text-xs text-lemon-chiffon bg-black/40 rounded px-2 py-1 max-w-xs overflow-x-auto">
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
