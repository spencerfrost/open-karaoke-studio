import React from "react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { useSessionStore } from "@/stores/sessionStore";
import { Users, Crown, Monitor, Smartphone, Clock } from "lucide-react";

interface SessionCodeDisplayProps {
  code: string;
  className?: string;
}

const SessionCodeDisplay: React.FC<SessionCodeDisplayProps> = ({ code, className = "" }) => {
  const { connectedDevices, isHost, deviceType, sessionInfo } = useSessionStore();

  if (!code) return null;

  const participantCount = connectedDevices.length;
  const deviceTypeIcons = {
    stage: Monitor,
    performer: Smartphone,
    controller: Smartphone,
  };

  const DeviceIcon = deviceTypeIcons[deviceType as keyof typeof deviceTypeIcons] || Smartphone;

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <div className={`absolute top-2 right-3 z-30 cursor-pointer ${className}`}>
          <div className="bg-orange-peel text-background px-3 py-1 rounded-lg font-mono text-lg font-bold hover:bg-orange-peel/90 transition-colors">
            {code}
          </div>
        </div>
      </HoverCardTrigger>
      <HoverCardContent className="w-80" side="bottom" align="end">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">Session Info</h4>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {sessionInfo?.created_at ? new Date(sessionInfo.created_at).toLocaleTimeString() : 'Unknown'}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-500" />
            <span className="text-sm">
              {participantCount} participant{participantCount !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <DeviceIcon className="h-4 w-4 text-green-500" />
            <span className="text-sm">
              You are {isHost ? 'the host' : 'a participant'}
              {isHost && <Crown className="inline h-3 w-3 ml-1 text-yellow-500" />}
            </span>
          </div>

          {connectedDevices.length > 0 && (
            <div className="border-t pt-2">
              <h5 className="text-xs font-medium text-muted-foreground mb-2">Connected Devices:</h5>
              <div className="space-y-1">
                {connectedDevices.map((device) => {
                  const DeviceTypeIcon = deviceTypeIcons[device.device_type as keyof typeof deviceTypeIcons] || Smartphone;
                  return (
                    <div key={device.device_id} className="flex items-center gap-2 text-xs">
                      <DeviceTypeIcon className="h-3 w-3" />
                      <span className={device.is_self ? 'font-medium' : ''}>
                        {device.device_type}
                        {device.is_self && ' (You)'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {sessionInfo?.expires_at && (
            <div className="text-xs text-muted-foreground border-t pt-2">
              Expires: {new Date(sessionInfo.expires_at).toLocaleString()}
            </div>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
};

export default SessionCodeDisplay;