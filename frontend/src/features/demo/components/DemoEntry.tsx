import React, { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { createLogger } from "@/lib/logger";
import { cn } from "@/lib/utils";
import { DemoStartError, useAuthStore } from "@/stores/authStore";
import { useDemoStatus } from "../hooks/useDemoStatus";

const logger = createLogger("component:DemoEntry");

const recordingUrl = import.meta.env.VITE_DEMO_RECORDING_URL?.trim() || null;

function startErrorMessage(error: unknown): string {
  const status = error instanceof DemoStartError ? error.status : null;
  const recording = recordingUrl
    ? " Or watch the recording in the meantime."
    : "";
  if (status === 503) {
    return (
      "Every demo seat is taken right now. A seat frees up when someone's " +
      `15 minutes run out, so try again in a few minutes.${recording}`
    );
  }
  if (status === 429) {
    return (
      "The demo has been started a lot from your network, so it's paused " +
      `for a while. Try again in an hour.${recording}`
    );
  }
  return `The demo couldn't start. Try again in a moment.${recording}`;
}

interface DemoEntryProps {
  /**
   * hero    - the computer layout: "Try it live" and "Watch the demo".
   * compact - phones: the recording only, since the live demo runs the TV
   *           screen and asks for a phone as the remote.
   */
  layout: "hero" | "compact";
  className?: string;
}

/**
 * DemoEntry - the entry page's way into the public demo, for anyone who
 * arrived without a session code or an account.
 *
 * "Try it live" signs in to a free demo pool account (its session is already
 * running) and the entry page sends demo accounts to the stage. It only shows
 * when the server has a demo pool. "Watch the demo" only shows when a
 * recording link is configured. With neither, this renders nothing.
 */
export const DemoEntry: React.FC<DemoEntryProps> = ({ layout, className }) => {
  const { enabled } = useDemoStatus();
  const startDemo = useAuthStore((state) => state.startDemo);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!enabled && !recordingUrl) return null;
  const showLive = enabled && layout === "hero";

  const handleTryLive = async () => {
    if (isStarting) return;
    setError(null);
    setIsStarting(true);
    try {
      // On success the entry page redirects (demo accounts go to the stage),
      // so there's nothing to reset.
      await startDemo();
    } catch (err) {
      logger.warn("Demo start failed:", err);
      setError(startErrorMessage(err));
      setIsStarting(false);
    }
  };

  const watchButton = recordingUrl && (
    <Button
      asChild
      variant="outline-foreground"
      className="h-14 px-6 font-display text-lg font-bold"
    >
      <a href={recordingUrl} target="_blank" rel="noopener noreferrer">
        Watch the demo
      </a>
    </Button>
  );

  if (layout === "compact") {
    return (
      <div className={cn("space-y-3", className)}>
        <p className="text-foreground-dim">
          Just looking?{" "}
          {enabled &&
            "The live demo runs the TV screen, so open this page on a computer to try it."}
        </p>
        {watchButton}
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex flex-wrap gap-3">
        {showLive && (
          <Button
            type="button"
            variant="primary"
            onClick={handleTryLive}
            data-tour="try-it-live"
            className="h-14 border-2 border-card-border px-6 font-display text-lg font-bold"
          >
            {isStarting ? "Starting..." : "Try it live"}
          </Button>
        )}
        {watchButton}
      </div>
      {showLive && (
        <p className="text-sm text-foreground-dim">
          Try it live opens a real 15-minute session on this server. You'll add
          a song from your phone, watch it process, and sing it.
        </p>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};
