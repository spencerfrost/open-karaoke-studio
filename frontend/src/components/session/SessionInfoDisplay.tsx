import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { useAccess } from "@/hooks/useAccess";
import { createLogger } from "@/lib/logger";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Crown,
  Monitor,
  Smartphone,
  Clock,
  LogOut,
  Minimize2,
} from "lucide-react";
import { QRCodeDisplay } from "@/features/queue";

const logger = createLogger("component:session-info-display");

interface SessionInfoDisplayProps {
  className?: string; // Applied to outermost wrapper
}

const SessionInfoDisplay: React.FC<SessionInfoDisplayProps> = ({
  className = "",
}) => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [fsContainer, setFsContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setFsContainer((document.fullscreenElement as HTMLElement) ?? null);
    const handleFullscreenChange = () => {
      setFsContainer((document.fullscreenElement as HTMLElement) ?? null);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener(
        "webkitfullscreenchange",
        handleFullscreenChange,
      );
    };
  }, []);

  const {
    displayCode,
    deviceType,
    connectedDevices,
    sessionInfo,
    leaveSession,
  } = useSessionStore();
  const { inSession, isStageDevice } = useAccess();

  const { connected } = useKaraokePlayerStore();

  // Only the host device gets a QR trigger to share.
  if (!inSession || !isStageDevice) return null;

  const handleLeaveSession = async () => {
    setIsOpen(false);
    // The store's leaveSession tells the server this device is gone before it
    // clears local state; clearing alone left the device listed as connected.
    try {
      await leaveSession();
    } catch (error) {
      logger.warn("Failed to leave session:", error);
    }
    navigate("/");
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) setIsPinned(false);
  };

  const handleTriggerClick = () => {
    const next = !isPinned;
    setIsPinned(next);
    setIsOpen(true);
  };

  const handleMouseEnter = () => setIsOpen(true);

  const handleMouseLeave = () => {
    if (!isPinned) setIsOpen(false);
  };

  const handleCollapse = () => {
    setIsCollapsed(true);
    setIsOpen(false);
    setIsPinned(false);
  };

  const participantCount = connectedDevices.length;
  const deviceTypeIcons = {
    stage: Monitor,
    performer: Smartphone,
    controller: Smartphone,
  };
  const DeviceIcon =
    deviceTypeIcons[deviceType as keyof typeof deviceTypeIcons] || Smartphone;

  // Collapsed trigger — a small pill to restore the widget
  if (isCollapsed) {
    return (
      <div className={className}>
        <button
          onClick={() => setIsCollapsed(false)}
          className="flex items-center gap-1 rounded-full bg-card/80 border border-border px-2 py-1 text-xs text-muted-foreground hover:text-card-foreground hover:bg-card transition-colors"
          title="Show session info"
        >
          <Users className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <div className={className}>
      <Popover open={isOpen} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <div
            onClick={handleTriggerClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            className="cursor-pointer"
          >
            <QRCodeDisplay
              value={`${window.location.origin}/join/${displayCode}`}
              size={100}
            />
          </div>
        </PopoverTrigger>
        <PopoverContent
          className="w-80"
          side="bottom"
          align="end"
          container={fsContainer}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Session Info</h4>
              <div className="flex items-center gap-1">
                <Badge
                  variant={connected ? "default" : "destructive"}
                  className="text-xs"
                >
                  {connected ? "Connected" : "Disconnected"}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={handleCollapse}
                  title="Minimize"
                >
                  <Minimize2 className="h-3 w-3" />
                </Button>
              </div>
            </div>

            {displayCode && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Session Code
                </span>
                <span className="font-mono text-lg font-bold">
                  {displayCode}
                </span>
              </div>
            )}

            <div className="flex items-center gap-2">
              <DeviceIcon className="h-4 w-4 text-success-strong" />
              <span className="text-sm">
                You are the host
                <Crown className="inline h-3 w-3 ml-1 text-warning-strong" />
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-info-strong" />
              <span className="text-sm">
                {participantCount} participant{participantCount !== 1 ? "s" : ""}
              </span>
            </div>

            {connectedDevices.length > 0 && (
              <div className="border-t pt-2">
                <h5 className="text-xs font-medium text-muted-foreground mb-2">
                  Connected Devices:
                </h5>
                <div className="space-y-1">
                  {connectedDevices.map((device) => {
                    const DeviceTypeIcon =
                      deviceTypeIcons[
                        device.device_type as keyof typeof deviceTypeIcons
                      ] || Smartphone;
                    return (
                      <div
                        key={device.device_id}
                        className="flex items-center gap-2 text-xs"
                      >
                        <DeviceTypeIcon className="h-3 w-3" />
                        <span className={device.is_self ? "font-medium" : ""}>
                          {device.display_name || device.device_type}
                          {device.is_self && " (You)"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {sessionInfo?.created_at && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground border-t pt-2">
                <Clock className="h-3 w-3" />
                <span>
                  Created: {new Date(sessionInfo.created_at).toLocaleTimeString()}
                </span>
              </div>
            )}

            {sessionInfo?.expires_at && (
              <div className="text-xs text-muted-foreground">
                Expires: {new Date(sessionInfo.expires_at).toLocaleString()}
              </div>
            )}

            <Separator />
            <div className="space-y-2">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleLeaveSession}
                className="w-full"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Leave Session
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                You will be disconnected from the session
              </p>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default SessionInfoDisplay;
