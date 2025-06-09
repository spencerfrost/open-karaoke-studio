import React from "react";
import { Badge } from "@/components/ui/badge";
import { Info, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MetadataQuality {
  percentage: number;
  level: "poor" | "fair" | "good" | "excellent";
  missingFields: string[];
  sourceCount: number;
}

interface MetadataQualityIndicatorProps {
  quality: MetadataQuality;
  size?: "small" | "medium" | "large";
  showDetails?: boolean;
  className?: string;
}

export const MetadataQualityIndicator: React.FC<MetadataQualityIndicatorProps> = ({
  quality,
  size = "medium",
  showDetails = false,
  className = "",
}) => {
  const getQualityColor = (level: MetadataQuality["level"]) => {
    switch (level) {
      case "poor":
        return "bg-red-100 text-red-800 border-red-200";
      case "fair":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "good":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "excellent":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getQualityIcon = (level: MetadataQuality["level"]) => {
    const iconSize = size === "small" ? 12 : size === "medium" ? 14 : 16;
    
    switch (level) {
      case "poor":
        return <XCircle size={iconSize} />;
      case "fair":
        return <AlertTriangle size={iconSize} />;
      case "good":
        return <Info size={iconSize} />;
      case "excellent":
        return <CheckCircle size={iconSize} />;
      default:
        return <Info size={iconSize} />;
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case "small":
        return "text-xs px-1.5 py-0.5";
      case "large":
        return "text-sm px-3 py-1.5";
      default:
        return "text-xs px-2 py-1";
    }
  };

  const badgeClasses = cn(
    "inline-flex items-center gap-1 font-medium border",
    getQualityColor(quality.level),
    getSizeClasses(),
    className
  );

  if (showDetails) {
    return (
      <div className={`space-y-2 ${className}`}>
        <Badge className={badgeClasses}>
          {getQualityIcon(quality.level)}
          {quality.percentage}% Complete
        </Badge>
        
        {quality.missingFields.length > 0 && (
          <div className="text-xs text-muted-foreground">
            <p>Missing: {quality.missingFields.join(", ")}</p>
          </div>
        )}
        
        <div className="text-xs text-muted-foreground">
          {quality.sourceCount} source{quality.sourceCount !== 1 ? "s" : ""} available
        </div>
      </div>
    );
  }

  return (
    <Badge className={badgeClasses}>
      {getQualityIcon(quality.level)}
      {size !== "small" && `${quality.percentage}%`}
    </Badge>
  );
};
