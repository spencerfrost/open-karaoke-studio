import React from "react";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import { SongProcessingStatus } from "@/types/Song";

interface ProcessingIndicatorProps {
  status: SongProcessingStatus;
  variant?: "badge" | "overlay" | "progress-bar";
}

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({
  status,
  variant = "overlay",
}) => {
  const getStatusText = () => {
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
  };

  const getStatusColor = () => {
    switch (status.status) {
      case "queued":
        return "bg-yellow-500";
      case "processing":
        return "bg-blue-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  if (variant === "badge") {
    return (
      <Badge className="absolute top-2 left-2 z-10" variant="secondary">
        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        {getStatusText()}
      </Badge>
    );
  }

  if (variant === "overlay") {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 z-30">
        <Loader2 className="w-12 h-12 text-white animate-spin mb-2" />
        <div className="text-white text-sm font-medium">{getStatusText()}</div>
        {status.message && (
          <div className="text-white/80 text-xs mt-1 px-4 text-center">
            {status.message}
          </div>
        )}
      </div>
    );
  }

  if (variant === "progress-bar") {
    return (
      <div className="absolute bottom-0 left-0 right-0 z-30">
        <div className="h-1.5 bg-gray-200">
          <div
            className={`h-full transition-all duration-300 ${getStatusColor()}`}
            style={{ width: `${status.progress}%` }}
          />
        </div>
        <div className="bg-black/80 px-2 py-1">
          <div className="text-white text-xs font-medium flex items-center justify-between">
            <span className="flex items-center">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              {getStatusText()}
            </span>
            {status.message && (
              <span className="text-white/70 ml-2 truncate">{status.message}</span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
};
