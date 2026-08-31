/**
 * RotationModeCard - the append/rotation queue-order toggle for the session
 * currently owned by this browser.
 *
 * Deliberately lives in Settings, not on the stage/TV screen or in
 * SessionInfoDisplay (which renders inside the stage's own SongSelectScreen) -
 * see docs/plans/2026-08-29-roster-and-rotation.md's open decisions. Only
 * ever shown to the session owner; a performer's phone never sees it.
 */

import React from "react";
import { Switch } from "@/components/ui/switch";
import { useSessionStore } from "@/stores/sessionStore";
import { useSetQueueOrderMode } from "@/hooks/api/useQueueOrderMode";
import { createLogger } from "@/lib/logger";

const logger = createLogger("component:RotationModeCard");

const RotationModeCard: React.FC = () => {
  const { sessionId, isSessionOwner, sessionInfo, refreshSessionInfo } =
    useSessionStore();
  const setMode = useSetQueueOrderMode(sessionId ?? undefined);

  if (!sessionId || !isSessionOwner) return null;

  const mode = sessionInfo?.queue_order_mode ?? "rotation";
  const isRotation = mode === "rotation";

  const handleToggle = (checked: boolean) => {
    setMode.mutate(
      { mode: checked ? "rotation" : "append" },
      {
        onSuccess: () => {
          void refreshSessionInfo();
        },
        onError: (error) => {
          logger.error("Failed to update queue order mode:", error);
        },
      },
    );
  };

  return (
    <div className="bg-card text-card-foreground shadow-lg border border-border overflow-hidden mb-4 p-4 rounded-lg">
      <h2 className="text-xl mb-3">Queue Order</h2>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="font-medium">
            {isRotation ? "Rotation" : "Append"}
          </div>
          <p className="text-sm opacity-75">
            {isRotation
              ? "Turns alternate fairly between everyone singing."
              : "Songs play in the order they were added."}
          </p>
        </div>
        <Switch
          checked={isRotation}
          disabled={setMode.isPending}
          onCheckedChange={handleToggle}
          aria-label="Toggle rotation queue ordering"
        />
      </div>
    </div>
  );
};

export default RotationModeCard;
