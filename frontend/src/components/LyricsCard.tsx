import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LyricsOption } from "@/hooks/api/useLyrics";
import { CheckCircle, ThumbsUp, AlertTriangle, XCircle } from "lucide-react";

// Helper function to get duration comparison status
const getDurationComparison = (
  songDuration: number,
  lyricsDuration: number
) => {
  const diff = Math.abs(songDuration - lyricsDuration);

  if (diff <= 0.5) {
    return {
      status: "perfect",
      message: "Perfect match",
      icon: CheckCircle,
      className: "text-green-700",
    };
  } else if (diff <= 2) {
    return {
      status: "good",
      message: "Good match",
      icon: ThumbsUp,
      className: "text-green-700",
    };
  } else if (diff <= 4) {
    return {
      status: "okay",
      message: "Okay match",
      icon: AlertTriangle,
      className: "text-orange-500",
    };
  } else {
    return {
      status: "poor",
      message: "Duration mismatch",
      icon: XCircle,
      className: "text-red-600",
    };
  }
};

interface LyricsCardProps {
  option: LyricsOption;
  selectedOption: LyricsOption | null;
  isBestMatch: boolean;
  parsedDuration: number;
  maxPreviewLines: number;
}

const LyricsCard: React.FC<LyricsCardProps> = ({
  option,
  selectedOption,
  isBestMatch,
  parsedDuration,
  maxPreviewLines,
}) => {
  if (!option) {
    return (
      <span className="text-muted-foreground italic">No lyrics available</span>
    );
  }

  const durationComparison = getDurationComparison(
    parsedDuration,
    option.duration ?? 0
  );
  const Icon = durationComparison.icon;

  // Remove timestamps for synced lyrics preview
  const cleanedLyrics = option.syncedLyrics
    ? option.syncedLyrics
        .split("\n")
        .map((line: string) => line.replace(/^\[\d+:\d+\.\d+\]/g, "").trim())
        .join("\n")
    : option.plainLyrics || "";

  // Only show first few lines
  const lines = cleanedLyrics?.split("\n").slice(0, maxPreviewLines) || [];

  // Helper function to format duration as mm:ss
  const formatDuration = (seconds: number) => {
    if (!seconds) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Card
      className={`hover:border-primary w-full ${
        selectedOption === option ? "border-primary bg-primary/5" : ""
      }`}
    >
      <CardContent className="p-3">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {option.syncedLyrics && (
                <Badge
                  variant="secondary"
                  className="bg-green-100 text-green-800 text-xs"
                >
                  Synced
                </Badge>
              )}
              {option.source && (
                <Badge variant="outline" className="text-xs">
                  {option.source}
                </Badge>
              )}
            </div>
          </div>

          {/* Duration comparison */}
          {option.duration && (
            <div className="flex flex-col items-end gap-1">
              <div
                className={`flex items-center gap-1 text-xs ${durationComparison.className}`}
              >
                {Icon && <Icon size={12} />}
                <span>{formatDuration(option.duration)}</span>
                <span className="text-muted-foreground">
                  vs {formatDuration(parsedDuration)}
                </span>
              </div>
              <div className={`text-xs ${durationComparison.className}`}>
                {isBestMatch ? "Best match" : durationComparison.message}
              </div>
            </div>
          )}
        </div>

        {/* Lyrics preview */}
        <div className="text-sm prose prose-sm max-w-none">
          <div className="max-h-32 overflow-hidden">
            {lines.map((line: string, i: number) => (
              <p key={i} className={line.trim() === "" ? "h-4" : ""}>
                {line}
              </p>
            ))}
            {cleanedLyrics?.split("\n").length > maxPreviewLines && (
              <p className="text-muted-foreground italic mt-2 border-t pt-1">
                {cleanedLyrics.split("\n").length - maxPreviewLines} more lines
                (not shown)
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default LyricsCard;
