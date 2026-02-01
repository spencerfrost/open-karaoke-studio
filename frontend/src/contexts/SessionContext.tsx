import React, { createContext, useEffect, useState, useCallback } from "react";
import { useSessionStore } from "@/stores/sessionStore";
import { createLogger } from "@/lib/logger";

const logger = createLogger("context:session");

export interface SessionContextType {
  isInitialized: boolean;
  isRecovering: boolean;
  sessionRequired: boolean;
  initializeSession: () => Promise<void>;
}

export const SessionContext = createContext<SessionContextType | undefined>(
  undefined,
);

interface SessionProviderProps {
  children: React.ReactNode;
  sessionRequired?: boolean;
}

export const SessionProvider: React.FC<SessionProviderProps> = ({
  children,
  sessionRequired = true,
}) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const { isRecovering, recoverSession, clearSession } = useSessionStore();

  const initializeSession = useCallback(async () => {
    if (isInitialized) return;

    logger.debug("🚀 SessionProvider: Initializing session recovery...");

    try {
      // Clear any previous session state
      clearSession();

      // Attempt session recovery
      await recoverSession();

      logger.debug("✅ SessionProvider: Session recovery completed");
    } catch (error) {
      logger.error("❌ SessionProvider: Session recovery failed:", error);
    } finally {
      setIsInitialized(true);
    }
  }, [isInitialized, clearSession, recoverSession]);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  const contextValue: SessionContextType = {
    isInitialized,
    isRecovering,
    sessionRequired,
    initializeSession,
  };

  // Don't render children until session initialization is complete
  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="vintage-texture-overlay" />
        <div className="text-center space-y-4 relative z-10">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">
            Initializing karaoke session...
          </p>
        </div>
      </div>
    );
  }

  return (
    <SessionContext.Provider value={contextValue}>
      {children}
    </SessionContext.Provider>
  );
};
