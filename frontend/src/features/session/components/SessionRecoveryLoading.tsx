import React from "react";
import { useSessionStore } from "@/stores/sessionStore";

const SessionRecoveryLoading: React.FC = () => {
  const { recoveryError } = useSessionStore();

  return (
    <div className="flex-1 flex items-center justify-center flex-col space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-orange-peel mb-4">
          Restoring Session
        </h2>
        <p className="text-lemon-chiffon/80 mb-8">
          Reconnecting to your previous karaoke session...
        </p>
        {recoveryError && (
          <div className="p-4 bg-destructive/20 border border-destructive/40 rounded-md mb-4">
            <p className="text-destructive text-center">{recoveryError}</p>
          </div>
        )}
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-peel"></div>
        </div>
      </div>
    </div>
  );
};

export default SessionRecoveryLoading;
