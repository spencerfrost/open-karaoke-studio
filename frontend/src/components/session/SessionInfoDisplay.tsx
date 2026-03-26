import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSessionStore } from "@/stores/sessionStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
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

type DisplayVariant = "code" | "qr" | "status" | "minimal";
type TriggerType = "click" | "hover" | "both";
type VisibilityMode = "host-only" | "all" | "performers-only";
type ColorScheme = "player" | "page";

interface ShowDetailsConfig {
  code?: boolean;
  participants?: boolean;
  deviceType?: boolean;
  logoutButton?: boolean;
  expiryTime?: boolean;
  connectionStatus?: boolean;
}

interface SessionInfoDisplayProps {
  // Core behavior
  variant?: DisplayVariant;
  trigger?: TriggerType;
  visibility?: VisibilityMode;
  colorScheme?: ColorScheme;
  showDetails?: ShowDetailsConfig;

  // Styling control - separated concerns
  className?: string; // Applied to outermost wrapper
  triggerClassName?: string; // Applied to trigger element (overrides variant defaults)
  contentClassName?: string; // Applied to content area inside popover

  // Popover positioning
  popoverSide?: "top" | "right" | "bottom" | "left";
  popoverAlign?: "start" | "center" | "end";
  popoverWidth?: string; // Default "w-80"

  // Code variant customization
  codeSize?: string; // e.g., "text-sm", "text-2xl" (default: "text-2xl")
  codePadding?: string; // e.g., "px-2 py-1", "px-4 py-2" (default: "px-4 py-2")

  // QR variant customization
  qrSize?: number; // QR code pixel size (default: 100)
}

const defaultShowDetails: ShowDetailsConfig = {
  code: true,
  participants: true,
  deviceType: true,
  logoutButton: true,
  expiryTime: true,
  connectionStatus: true,
};

const SessionInfoDisplay: React.FC<SessionInfoDisplayProps> = ({
  variant = "status",
  trigger = "click",
  visibility = "all",
  colorScheme = "player",
  showDetails = defaultShowDetails,
  className = "",
  triggerClassName = "",
  contentClassName = "",
  popoverSide = "bottom",
  popoverAlign = "end",
  popoverWidth = "w-80",
  codeSize = "text-2xl",
  codePadding = "px-4 py-2",
  qrSize = 100,
}) => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeVariant, setActiveVariant] = useState<DisplayVariant>(variant);
  const [activeQrSize, setActiveQrSize] = useState(qrSize);
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
        handleFullscreenChange
      );
    };
  }, []);

  const {
    sessionId,
    displayCode,
    isHost,
    deviceType,
    connectedDevices,
    sessionInfo,
    clearSession,
  } = useSessionStore();

  const { connected } = useKaraokePlayerStore();

  // Check visibility
  if (!sessionId) return null;
  if (visibility === "host-only" && !isHost) return null;
  if (visibility === "performers-only" && isHost) return null;

  const handleLogout = () => {
    sessionWebSocketService.disconnect();
    clearSession();
    setIsOpen(false);
    navigate("/");
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) setIsPinned(false);
  };

  const handleTriggerClick = () => {
    if (trigger === "click") return; // Radix Popover handles open/close natively
    const next = !isPinned;
    setIsPinned(next);
    setIsOpen(true);
  };

  const handleMouseEnter = () => {
    if (trigger !== "click") setIsOpen(true);
  };

  const handleMouseLeave = () => {
    if (trigger !== "click" && !isPinned) setIsOpen(false);
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

  // Merge user config with defaults
  const details = { ...defaultShowDetails, ...showDetails };

  // Color schemes for code variant
  const codeColorSchemes = {
    player: "bg-orange-peel text-background hover:bg-orange-peel/90",
    page: "bg-card text-foreground hover:bg-card/90 border border-border",
  };

  // Collapsed trigger — a small pill to restore the widget
  if (isCollapsed) {
    return (
      <div className={className}>
        <button
          onClick={() => setIsCollapsed(false)}
          className="flex items-center gap-1 rounded-full bg-card/80 border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-card transition-colors"
          title="Show session info"
        >
          <Users className="h-3 w-3" />
        </button>
      </div>
    );
  }

  // Render the trigger based on active variant
  const renderTrigger = () => {
    const baseTriggerClass = triggerClassName || "";

    switch (activeVariant) {
      case "code":
        return (
          <div
            className={`${codePadding} rounded-lg font-mono ${codeSize} font-bold transition-colors cursor-pointer ${codeColorSchemes[colorScheme]} ${baseTriggerClass}`}
          >
            {displayCode}
          </div>
        );

      case "qr":
        // Performer devices never display a QR code
        if (!isHost) return null;
        return (
          <div className={`cursor-pointer ${baseTriggerClass}`}>
            <QRCodeDisplay
              value={`${window.location.origin}/join/${displayCode}`}
              size={activeQrSize}
            />
          </div>
        );

      case "status":
        return (
          <div
            className={`flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition-opacity ${baseTriggerClass}`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                connected
                  ? "bg-dark-cyan animate-pulse"
                  : "bg-rust animate-pulse"
              }`}
            />
            <span
              className={`text-xs font-medium ${
                connected ? "text-dark-cyan" : "text-rust"
              }`}
            >
              {connected ? "Live" : "Offline"}
            </span>
          </div>
        );

      case "minimal":
        return (
          <div
            className={`flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition-opacity ${baseTriggerClass}`}
          >
            <Users className="h-4 w-4" />
            <span className="text-sm font-medium">{displayCode}</span>
          </div>
        );

      default:
        return null;
    }
  };

  // Render the content
  const renderContent = () => (
    <div className={`space-y-3 ${contentClassName}`}>
      {/* Header with connection status and collapse button */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Session Info</h4>
        <div className="flex items-center gap-1">
          {details.connectionStatus && (
            <Badge
              variant={connected ? "default" : "destructive"}
              className="text-xs"
            >
              {connected ? "Connected" : "Disconnected"}
            </Badge>
          )}
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

      {/* Variant switcher */}
      <div className="flex gap-1 border-b pb-2">
        {(["code", "qr", "status", "minimal"] as DisplayVariant[]).map((v) => (
          <Button
            key={v}
            variant={activeVariant === v ? "default" : "ghost"}
            size="sm"
            className="h-6 text-xs px-2"
            disabled={v === "qr" && !isHost}
            onClick={() => setActiveVariant(v)}
          >
            {v}
          </Button>
        ))}
      </div>

      {activeVariant === "qr" && isHost && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground shrink-0">Size</span>
          <Slider
            min={60}
            max={300}
            step={10}
            value={[activeQrSize]}
            onValueChange={([v]) => setActiveQrSize(v)}
            className="flex-1"
          />
          <span className="text-xs text-muted-foreground w-8 text-right">
            {activeQrSize}
          </span>
        </div>
      )}

      {details.code && displayCode && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Session Code</span>
          <span className="font-mono text-lg font-bold">{displayCode}</span>
        </div>
      )}

      {details.deviceType && (
        <div className="flex items-center gap-2">
          <DeviceIcon className="h-4 w-4 text-green-500" />
          <span className="text-sm">
            You are {isHost ? "the host" : "a participant"}
            {isHost && (
              <Crown className="inline h-3 w-3 ml-1 text-yellow-500" />
            )}
          </span>
        </div>
      )}

      {details.participants && (
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-blue-500" />
          <span className="text-sm">
            {participantCount} participant{participantCount !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {details.participants && connectedDevices.length > 0 && (
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

      {details.expiryTime && sessionInfo?.created_at && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground border-t pt-2">
          <Clock className="h-3 w-3" />
          <span>
            Created: {new Date(sessionInfo.created_at).toLocaleTimeString()}
          </span>
        </div>
      )}

      {details.expiryTime && sessionInfo?.expires_at && (
        <div className="text-xs text-muted-foreground">
          Expires: {new Date(sessionInfo.expires_at).toLocaleString()}
        </div>
      )}

      {details.logoutButton && (
        <>
          <Separator />
          <div className="space-y-2">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleLogout}
              className="w-full"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Leave Session
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              {isHost
                ? "This will end the session for all participants"
                : "You will be disconnected from the session"}
            </p>
          </div>
        </>
      )}
    </div>
  );

  return (
    <div className={className}>
      <Popover open={isOpen} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <div
            onClick={handleTriggerClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            {renderTrigger()}
          </div>
        </PopoverTrigger>
        <PopoverContent
          className={popoverWidth}
          side={popoverSide}
          align={popoverAlign}
          container={fsContainer}
          onMouseEnter={() => {
            if (trigger !== "click") setIsOpen(true);
          }}
          onMouseLeave={() => {
            if (trigger !== "click" && !isPinned) setIsOpen(false);
          }}
        >
          {renderContent()}
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default SessionInfoDisplay;
