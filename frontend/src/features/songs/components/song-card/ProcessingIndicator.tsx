import React from "react";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { SongProcessingStatus } from "@/types/Song";

interface ProcessingIndicatorProps {
  status: SongProcessingStatus;
  variant?: "badge" | "overlay" | "progress-bar";
}

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({
  status,
  variant = "overlay",
}) => {
  const isError = status.status === "error";
  const Icon = isError ? AlertCircle : Loader2;
  const getStatusText = () => {
    switch (status.rawStatus) {
      case "pending":
        return "Queued";
      case "downloading":
        return "Downloading";
      case "processing":
        return `Separating Audio ${status.progress}%`;
      case "failed":
      case "cancelled":
        return "Failed";
      default:
        switch (status.status) {
          case "queued":
            return "Queued";
          case "processing":
            return `Processing ${status.progress}%`;
          case "error":
            return "Failed";
          default:
            return "Processing";
        }
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case "queued":
        return "bg-warning";
      case "processing":
        return "bg-info";
      case "error":
        return "bg-destructive";
      default:
        return "bg-muted";
    }
  };

  if (variant === "badge") {
    return (
      <Badge className="absolute top-2 left-2 z-10" variant="secondary">
        <Icon className={cn("w-3 h-3 mr-1", !isError && "animate-spin")} />
        {getStatusText()}
      </Badge>
    );
  }

  if (variant === "overlay") {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-overlay/70 z-30">
        <Icon
          className={cn(
            "w-12 h-12 text-foreground mb-2",
            !isError && "animate-spin",
          )}
        />
        <div className="text-foreground text-sm font-medium">
          {getStatusText()}
        </div>
        {status.message && (
          <div className="text-foreground/80 text-xs mt-1 px-4 text-center">
            {status.message}
          </div>
        )}
      </div>
    );
  }

  if (variant === "progress-bar") {
    return (
      <div className="absolute bottom-0 left-0 right-0 z-30">
        <div className="h-1.5 bg-muted">
          <div
            className={`h-full transition-all duration-300 ${getStatusColor()}`}
            style={{ width: `${status.progress}%` }}
          />
        </div>
        <div className="bg-overlay/80 px-2 py-1">
          <div className="text-foreground text-xs font-medium flex items-center justify-between">
            <span className="flex items-center">
              <Icon
                className={cn("w-3 h-3 mr-1", !isError && "animate-spin")}
              />
              {getStatusText()}
            </span>
            {status.message && (
              <span className="text-foreground/70 ml-2 truncate">
                {status.message}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
};
